"""Durable candidate registration for owner-operated methods documents."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import stat
import uuid
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConfigurationError, ConflictError, IntegrityError
from research_system.git_execution import run_git
from research_system.store.durability import fsync_directory


class CommandSubmitter(Protocol):
    def submit(self, envelope: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class CandidateRegistration:
    """Caller-authorized production metadata for one immutable document."""

    artefact_id: str
    project_id: str
    actor_id: str
    authority_grant_id: str
    submitted_at: str
    correlation_id: str
    reason: str
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RegisteredCandidate:
    artefact_id: str
    content_sha256: str
    raw_bytes: bytes
    relative_path: str
    receipt: Any


@dataclass(frozen=True)
class PreparedRawRegistration:
    """Fully validated raw publication material with no durable side effect."""

    registration: CandidateRegistration
    publication: RawContentPublication
    raw_bytes: bytes
    command: dict[str, Any]


@dataclass(frozen=True)
class PreparedCandidateRegistration:
    value: dict[str, Any]
    registration: CandidateRegistration
    raw_bytes: bytes
    content_sha256: str
    relative_path: str
    command: dict[str, Any]


class CandidateDocumentStore:
    """Write exact canonical bytes once beneath the configured control root."""

    def __init__(
        self,
        control_root: Path,
        *,
        root_id: str = "control",
        relative_directory: Path = Path("methods/documents"),
    ) -> None:
        self.control_root = control_root.resolve(strict=True)
        self.root_id = root_id
        if relative_directory.is_absolute() or ".." in relative_directory.parts:
            raise ValueError("candidate document directory must be control-relative")
        self.relative_directory = relative_directory

    def relative_path(self, artefact_id: str) -> str:
        """Return the final control-relative path without publishing bytes."""
        return (self.relative_directory / f"{artefact_id}.json").as_posix()

    def _write(self, artefact_id: str, raw_bytes: bytes) -> str:
        relative = Path(self.relative_path(artefact_id))
        _publish_contained_file_no_replace(
            self.control_root,
            relative.as_posix(),
            raw_bytes,
            conflict_message="methods document identity already binds different bytes",
        )
        return relative.as_posix()

    def write(self, artefact_id: str, raw_bytes: bytes) -> str:
        """Publish candidate document bytes through the historical public seam."""

        return self._write(artefact_id, raw_bytes)

    def publish_bytes(self, artefact_id: str, raw_bytes: bytes) -> str:
        """Publish non-artefact coordinator bytes without resembling an ObjectStore kind call."""

        return self._write(artefact_id, raw_bytes)


@dataclass(frozen=True)
class RawContentPublication:
    """Exact committed raw content admitted to the owner-operated brief seam."""

    source_relative_path: str
    source_git_blob: str
    content_sha256: str
    size_bytes: int
    media_type: str
    document_type: str
    destination_relative_path: str


_SPEC_SOURCE_PATHS = frozenset(
    {
        ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
        ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
    }
)
_METHODS_ASSET_PREFIX = ".research-system/methods/assets/"
_RAW_DESTINATION_PREFIX = "methods/content/spec-flow/"
_REGISTRATION_RECOVERY_DIRECTORY = Path("runtime/registered-content-recovery")
_REGISTRATION_RECOVERY_SCHEMA_ID = "ars://internal/registered-content-recovery"


def spec_brief_input_artefact_id(source_relative_path: str, content_sha256: str) -> str:
    """Derive the sole artefact identity for one exact governed brief input."""

    path = Path(source_relative_path)
    posix = path.as_posix()
    allowed = posix in _SPEC_SOURCE_PATHS or (
        posix.startswith(_METHODS_ASSET_PREFIX)
        and path.parent.as_posix() == _METHODS_ASSET_PREFIX.rstrip("/")
        and path.suffix == ".md"
    )
    if (
        path.is_absolute()
        or ".." in path.parts
        or posix != source_relative_path
        or not allowed
        or not isinstance(content_sha256, str)
        or len(content_sha256) != 64
        or any(character not in "0123456789abcdef" for character in content_sha256)
    ):
        raise ConfigurationError("SPEC brief input identity is invalid")
    digest = bytearray(
        hashlib.sha256(
            canonical_bytes(
                {
                    "kind": "spec-brief-input",
                    "source_relative_path": source_relative_path,
                    "content_sha256": content_sha256,
                }
            )
        ).digest()[:16]
    )
    digest[6] = (digest[6] & 0x0F) | 0x70
    digest[8] = (digest[8] & 0x3F) | 0x80
    return f"art_{uuid.UUID(bytes=bytes(digest))}"


def _require_physical_destination(control_root: Path, relative_path: str, *, create: bool = False) -> Path:
    root = control_root.resolve(strict=True)
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        raise ConfigurationError("raw content destination is not canonical and control-relative")
    current = root
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    missing_parent = False
    for part in relative.parts[:-1]:
        current = current / part
        if missing_parent and not create:
            continue
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if not create:
                missing_parent = True
                continue
            try:
                current.mkdir()
                metadata = current.lstat()
            except OSError as exc:
                raise ConfigurationError("raw content destination parent is unavailable") from exc
        except OSError as exc:
            raise ConfigurationError("raw content destination parent is unavailable") from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & reparse
        ):
            raise ConfigurationError("raw content destination parent is not a physical directory")
    target = current / relative.name
    if not missing_parent and (target.exists() or target.is_symlink()):
        try:
            metadata = target.lstat()
        except OSError as exc:
            raise ConfigurationError("raw content destination is unavailable") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & reparse
        ):
            raise ConfigurationError("raw content destination is not a physical regular file")
    return target


def _hold_windows_directories(paths: list[Path]) -> list[int]:
    """Hold physical directory handles without delete sharing during a pathname create."""

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (ctypes.c_void_p,)
    close_handle.restype = ctypes.c_int
    invalid = ctypes.c_void_p(-1).value
    handles: list[int] = []
    flags = 0x02000000 | 0x00200000  # FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT
    try:
        for path in paths:
            desired_access = 0x0001 | 0x0080 | 0x00100000  # LIST_DIRECTORY | READ_ATTRIBUTES | SYNCHRONIZE
            handle = create_file(str(path), desired_access, 0x1 | 0x2, None, 3, flags, None)
            if handle == invalid:
                raise OSError(ctypes.get_last_error(), "physical destination directory is unavailable")
            handles.append(int(handle))
            metadata = path.lstat()
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0) & 0x400
            ):
                raise ConfigurationError("raw content destination parent is not a physical directory")
        return handles
    except Exception:
        for handle in reversed(handles):
            close_handle(ctypes.c_void_p(handle))
        raise


def _open_windows_relative_file(parent_handle: int, name: str, *, create: bool) -> int:
    """Open a leaf relative to a held Windows directory without following reparses."""

    import ctypes
    import msvcrt

    class UnicodeString(ctypes.Structure):
        _fields_ = (
            ("Length", ctypes.c_ushort),
            ("MaximumLength", ctypes.c_ushort),
            ("Buffer", ctypes.c_wchar_p),
        )

    class ObjectAttributes(ctypes.Structure):
        _fields_ = (
            ("Length", ctypes.c_ulong),
            ("RootDirectory", ctypes.c_void_p),
            ("ObjectName", ctypes.POINTER(UnicodeString)),
            ("Attributes", ctypes.c_ulong),
            ("SecurityDescriptor", ctypes.c_void_p),
            ("SecurityQualityOfService", ctypes.c_void_p),
        )

    class IoStatusBlock(ctypes.Structure):
        _fields_ = (("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t))

    buffer = ctypes.create_unicode_buffer(name)
    encoded_length = len(name.encode("utf-16-le"))
    unicode_name = UnicodeString(encoded_length, encoded_length + 2, ctypes.cast(buffer, ctypes.c_wchar_p))
    attributes = ObjectAttributes(
        ctypes.sizeof(ObjectAttributes),
        ctypes.c_void_p(parent_handle),
        ctypes.pointer(unicode_name),
        0x40,  # OBJ_CASE_INSENSITIVE
        None,
        None,
    )
    status_block = IoStatusBlock()
    native_handle = ctypes.c_void_p()
    nt_create_file = ctypes.WinDLL("ntdll").NtCreateFile
    nt_create_file.argtypes = (
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_ulong,
        ctypes.POINTER(ObjectAttributes),
        ctypes.POINTER(IoStatusBlock),
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
    )
    nt_create_file.restype = ctypes.c_long
    desired_access = (0x40000000 if create else 0x80000000) | 0x00000080 | 0x00100000
    options = 0x40 | 0x20 | (0 if create else 0x00200000)
    status = nt_create_file(
        ctypes.byref(native_handle),
        desired_access,
        ctypes.byref(attributes),
        ctypes.byref(status_block),
        None,
        0x80 if create else 0,  # FILE_ATTRIBUTE_NORMAL
        0x1,  # FILE_SHARE_READ
        2 if create else 1,  # FILE_CREATE / FILE_OPEN
        options,
        None,
        0,
    )
    if status & 0xFFFFFFFF == 0xC0000035:  # STATUS_OBJECT_NAME_COLLISION
        raise FileExistsError(name)
    if status & 0xFFFFFFFF in {0xC0000034, 0xC000003A}:  # name/path not found
        raise FileNotFoundError(name)
    if status < 0 or not native_handle.value:
        operation = "created" if create else "opened"
        raise OSError(status, f"raw content destination leaf could not be {operation}")
    try:
        access = os.O_WRONLY if create else os.O_RDONLY
        return msvcrt.open_osfhandle(native_handle.value, access | os.O_BINARY)
    except Exception:
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(native_handle)
        raise


def _open_windows_relative_new_file(parent_handle: int, name: str) -> int:
    """Create a new leaf relative to an already verified directory handle."""

    return _open_windows_relative_file(parent_handle, name, create=True)


def _open_windows_relative_existing_file(parent_handle: int, name: str) -> int:
    """Open an existing regular leaf relative to a held physical directory."""

    return _open_windows_relative_file(parent_handle, name, create=False)


@contextmanager
def _hold_contained_parent(control_root: Path, relative_path: str) -> Iterator[tuple[int, Path]]:
    """Hold the verified parent used for an atomic directory-entry publication."""

    target = _require_physical_destination(control_root, relative_path, create=True)
    root = control_root.resolve(strict=True)
    relative = Path(relative_path)
    directory_descriptors: list[int] = []
    windows_handles: list[int] = []
    try:
        if os.open in os.supports_dir_fd and hasattr(os, "O_DIRECTORY"):
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
            directory_descriptors.append(os.open(root, directory_flags))
            for part in relative.parts[:-1]:
                directory_descriptors.append(os.open(part, directory_flags, dir_fd=directory_descriptors[-1]))
            yield directory_descriptors[-1], target
        elif os.name == "nt":
            parents = [root]
            for part in relative.parts[:-1]:
                parents.append(parents[-1] / part)
            windows_handles = _hold_windows_directories(parents)
            yield windows_handles[-1], target
        else:
            raise ConfigurationError("atomic contained file publication is unsupported on this platform")
    finally:
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)
        if windows_handles:
            import ctypes

            close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
            for handle in reversed(windows_handles):
                close_handle(ctypes.c_void_p(handle))


def _after_contained_file_fsync(_temporary: Path, _target: Path) -> None:
    """Test seam after staging is durable but before the final name exists."""


def _after_contained_file_linked(_temporary: Path, _target: Path) -> None:
    """Test seam after the final hard link exists but before it is verified."""


def _held_parent_matches_destination(parent_descriptor: int, held_target: Path) -> None:
    """Reject a POSIX pathname redirect after the parent directory was opened."""

    if os.name == "nt":
        # _hold_windows_directories omits FILE_SHARE_DELETE, so the held parent
        # cannot be renamed or replaced while the relative leaf operation runs.
        return
    try:
        current_parent = held_target.parent.lstat()
    except OSError as exc:
        raise IntegrityError("publication destination parent changed while held") from exc
    held_parent = os.fstat(parent_descriptor)
    if (
        not stat.S_ISDIR(current_parent.st_mode)
        or stat.S_ISLNK(current_parent.st_mode)
        or not os.path.samestat(held_parent, current_parent)
    ):
        raise IntegrityError("publication destination parent changed while held")


def _held_contained_file_identity(parent_descriptor: int, held_target: Path, name: str) -> os.stat_result:
    """Read a physical leaf identity relative to the held parent directory."""

    if os.name == "nt":
        # The held directory handle excludes delete sharing, which keeps this
        # pathname bound to that physical parent.  Reopening the staging inode
        # relative to the parent would violate its intentionally exclusive
        # sharing mode, so inspect the leaf through the protected pathname.
        identity = held_target.with_name(name).lstat()
    else:
        identity = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if (
        not stat.S_ISREG(identity.st_mode)
        or stat.S_ISLNK(identity.st_mode)
        or getattr(identity, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    ):
        raise ConfigurationError("publication destination is not a physical regular file")
    return identity


def _read_held_contained_file(parent_descriptor: int, held_target: Path, name: str) -> bytes:
    """Read an existing regular leaf relative to the already-held parent."""

    if os.name == "nt":
        descriptor = _open_windows_relative_existing_file(parent_descriptor, name)
    else:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_descriptor,
        )
    try:
        identity = os.fstat(descriptor)
        if (
            not stat.S_ISREG(identity.st_mode)
            or stat.S_ISLNK(identity.st_mode)
            or getattr(identity, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ConfigurationError("publication destination is not a physical regular file")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _remove_held_created_file(
    parent_descriptor: int,
    held_target: Path,
    name: str,
    identity: os.stat_result,
) -> None:
    """Remove one attempt-owned leaf while its verified parent remains held."""

    try:
        current = _held_contained_file_identity(parent_descriptor, held_target, name)
    except (ConfigurationError, OSError):
        return
    if not os.path.samestat(current, identity):
        return
    try:
        if os.name == "nt":
            held_target.with_name(name).unlink()
        else:
            os.unlink(name, dir_fd=parent_descriptor)
    except OSError:
        return
    try:
        if os.name == "nt":
            fsync_directory(held_target.parent)
        else:
            os.fsync(parent_descriptor)
    except OSError:
        pass


def _publish_contained_file_no_replace(
    control_root: Path,
    relative_path: str,
    data: bytes,
    *,
    conflict_message: str,
) -> None:
    """Durably stage then atomically publish one complete contained leaf."""

    relative = Path(relative_path)
    temporary_relative = relative.with_name(f".{relative.name}.{uuid.uuid4().hex}.tmp")
    temporary_target = control_root.resolve(strict=True) / temporary_relative
    temporary_identity: os.stat_result | None = None
    cleanup_staging = True
    try:
        with _open_new_contained_file(control_root, temporary_relative.as_posix()) as (fd, opened_target):
            temporary_target = opened_target
            with os.fdopen(fd, "wb") as handle:
                temporary_identity = os.fstat(handle.fileno())
                if not stat.S_ISREG(temporary_identity.st_mode):
                    raise ConfigurationError("publication staging destination is not a physical regular file")
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
                target = control_root / relative
                _after_contained_file_fsync(temporary_target, target)
                with _hold_contained_parent(control_root, relative_path) as (parent_descriptor, held_target):
                    temporary_name = temporary_relative.name
                    final_link_created = False
                    cleanup_final_link = False
                    try:
                        try:
                            source_identity = (
                                temporary_target.lstat()
                                if os.name == "nt"
                                else _held_contained_file_identity(
                                    parent_descriptor,
                                    held_target,
                                    temporary_name,
                                )
                            )
                            if not os.path.samestat(temporary_identity, source_identity):
                                raise IntegrityError("publication staging identity changed before finalization")
                            if os.name == "nt":
                                os.link(held_target.parent / temporary_name, held_target, follow_symlinks=False)
                            else:
                                os.link(
                                    temporary_name,
                                    relative.name,
                                    src_dir_fd=parent_descriptor,
                                    dst_dir_fd=parent_descriptor,
                                    follow_symlinks=False,
                                )
                            final_link_created = True
                            _after_contained_file_linked(temporary_target, held_target)
                        except FileExistsError:
                            if _read_held_contained_file(parent_descriptor, held_target, relative.name) != data:
                                raise ConflictError(conflict_message) from None
                        else:
                            try:
                                _held_parent_matches_destination(parent_descriptor, held_target)
                                destination_identity = _held_contained_file_identity(
                                    parent_descriptor,
                                    held_target,
                                    relative.name,
                                )
                                if not os.path.samestat(temporary_identity, destination_identity):
                                    # This name now belongs to another writer.
                                    # Never unlink a foreign final entry.
                                    raise IntegrityError("published file identity differs from held staging file")
                            except (ConfigurationError, FileNotFoundError, IntegrityError, OSError):
                                cleanup_final_link = final_link_created
                                raise
                            if os.name != "nt":
                                os.fsync(parent_descriptor)
                            else:
                                fsync_directory(held_target.parent)
                    except BaseException as exc:
                        if not isinstance(exc, Exception):
                            cleanup_staging = False
                        raise
                    finally:
                        if cleanup_staging and os.name != "nt":
                            if cleanup_final_link:
                                _remove_held_created_file(
                                    parent_descriptor,
                                    held_target,
                                    relative.name,
                                    temporary_identity,
                                )
                            _remove_held_created_file(
                                parent_descriptor,
                                held_target,
                                temporary_name,
                                temporary_identity,
                            )
                            cleanup_staging = False
    except BaseException as exc:
        if not isinstance(exc, Exception):
            cleanup_staging = False
        if temporary_identity is not None:
            if cleanup_staging:
                _remove_created_file(temporary_target, temporary_identity)
        raise
    finally:
        if cleanup_staging and temporary_identity is not None:
            _remove_created_file(temporary_target, temporary_identity)


@contextmanager
def _open_new_contained_file(control_root: Path, relative_path: str) -> Iterator[tuple[int, Path]]:
    """Create one leaf while its trusted parent chain remains bound."""

    target = _require_physical_destination(control_root, relative_path, create=True)
    root = control_root.resolve(strict=True)
    relative = Path(relative_path)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    directory_descriptors: list[int] = []
    windows_handles: list[int] = []
    descriptor = -1
    try:
        if os.open in os.supports_dir_fd and hasattr(os, "O_DIRECTORY"):
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
            directory_descriptors.append(os.open(root, directory_flags))
            for part in relative.parts[:-1]:
                directory_descriptors.append(os.open(part, directory_flags, dir_fd=directory_descriptors[-1]))
            descriptor = os.open(relative.name, flags, 0o600, dir_fd=directory_descriptors[-1])
        elif os.name == "nt":
            parents = [root]
            for part in relative.parts[:-1]:
                parents.append(parents[-1] / part)
            windows_handles = _hold_windows_directories(parents)
            descriptor = _open_windows_relative_new_file(windows_handles[-1], relative.name)
        else:
            raise ConfigurationError("atomic contained file creation is unsupported on this platform")
        owned_descriptor = descriptor
        descriptor = -1
        yield owned_descriptor, target
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)
        if windows_handles:
            import ctypes

            close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
            for handle in reversed(windows_handles):
                close_handle(ctypes.c_void_p(handle))


@contextmanager
def _open_existing_contained_file(control_root: Path, relative_path: str) -> Iterator[tuple[int, Path]]:
    """Open one existing leaf while retaining its verified physical parent chain."""

    target = _require_physical_destination(control_root, relative_path)
    root = control_root.resolve(strict=True)
    relative = Path(relative_path)
    directory_descriptors: list[int] = []
    windows_handles: list[int] = []
    descriptor = -1
    try:
        if os.open in os.supports_dir_fd and hasattr(os, "O_DIRECTORY"):
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
            directory_descriptors.append(os.open(root, directory_flags))
            for part in relative.parts[:-1]:
                directory_descriptors.append(os.open(part, directory_flags, dir_fd=directory_descriptors[-1]))
            descriptor = os.open(
                relative.name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_descriptors[-1],
            )
        elif os.name == "nt":
            parents = [root]
            for part in relative.parts[:-1]:
                parents.append(parents[-1] / part)
            windows_handles = _hold_windows_directories(parents)
            descriptor = _open_windows_relative_existing_file(windows_handles[-1], relative.name)
        else:
            raise ConfigurationError("atomic contained file reading is unsupported on this platform")
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ConfigurationError("raw content destination is not a physical regular file")
        owned_descriptor = descriptor
        descriptor = -1
        yield owned_descriptor, target
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)
        if windows_handles:
            import ctypes

            close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
            for handle in reversed(windows_handles):
                close_handle(ctypes.c_void_p(handle))


def _read_existing_contained_file(control_root: Path, relative_path: str) -> bytes:
    with _open_existing_contained_file(control_root, relative_path) as (fd, _target):
        with os.fdopen(fd, "rb") as handle:
            return handle.read()


def _remove_created_file(target: Path, identity: os.stat_result) -> None:
    """Remove only the exact leaf created by the failed publication attempt."""

    try:
        current = target.lstat()
        if (
            stat.S_ISREG(current.st_mode)
            and not stat.S_ISLNK(current.st_mode)
            and current.st_dev == identity.st_dev
            and current.st_ino == identity.st_ino
        ):
            target.unlink()
            try:
                fsync_directory(target.parent)
            except OSError:
                pass
    except FileNotFoundError:
        pass


def _git(repository_root: Path, *arguments: str) -> str:
    result = run_git(
        repository_root,
        *arguments,
        unavailable_message="raw content Git binding is unavailable",
    )
    if result.returncode != 0:
        raise ConfigurationError("raw content Git binding is unavailable")
    return result.stdout.strip()


def _validate_committed_raw_source(repository_root: Path, publication: RawContentPublication) -> bytes:
    root = repository_root.resolve(strict=True)
    if Path(_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True) != root:
        raise ConfigurationError("raw content repository is not the configured Git worktree root")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise ConfigurationError("raw content repository is not clean")
    relative = Path(publication.source_relative_path)
    posix = relative.as_posix()
    allowed = posix in _SPEC_SOURCE_PATHS or (
        posix.startswith(_METHODS_ASSET_PREFIX)
        and relative.parent.as_posix() == _METHODS_ASSET_PREFIX.rstrip("/")
        and relative.suffix == ".md"
    )
    if relative.is_absolute() or ".." in relative.parts or not allowed or "scale" in posix.casefold():
        raise ConfigurationError("raw content source is outside the SPEC brief allowlist")
    expected_document_type = "spec_operator_source" if posix in _SPEC_SOURCE_PATHS else "methods_asset"
    if publication.document_type != expected_document_type:
        raise ConfigurationError("raw content document type does not match its source path")
    if publication.media_type != "text/markdown; charset=utf-8":
        raise ConfigurationError("raw content media type is unsupported")
    destination = Path(publication.destination_relative_path)
    destination_posix = destination.as_posix()
    if (
        destination.is_absolute()
        or ".." in destination.parts
        or not destination_posix.startswith(_RAW_DESTINATION_PREFIX)
        or destination.suffix != ".md"
    ):
        raise ConfigurationError("raw content destination is outside the SPEC content root")
    source = (root / relative).resolve(strict=True)
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ConfigurationError("raw content source escapes the repository") from exc
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ConfigurationError("raw content source is unavailable") from exc
    committed_blob = _git(root, "rev-parse", f"HEAD:{posix}")
    working_result = run_git(
        root,
        "hash-object",
        "--path",
        posix,
        "--stdin",
        input=raw,
        text=False,
        unavailable_message="raw content Git binding is unavailable",
    )
    if working_result.returncode != 0:
        raise ConfigurationError("raw content Git binding is unavailable")
    try:
        working_blob = working_result.stdout.decode("ascii").strip()
    except (AttributeError, UnicodeError) as exc:
        raise ConfigurationError("raw content Git binding returned invalid output") from exc
    if committed_blob != publication.source_git_blob or working_blob != committed_blob:
        raise ConfigurationError("raw content source is not the exact committed Git blob")
    if len(raw) != publication.size_bytes or sha256_hex(raw) != publication.content_sha256:
        raise ConfigurationError("raw content byte binding differs")
    return raw


def _write_immutable_raw(control_root: Path, relative_path: str, raw: bytes) -> None:
    _publish_contained_file_no_replace(
        control_root,
        relative_path,
        raw,
        conflict_message="raw content destination already binds different bytes",
    )


def _registration_event_matches(event: object, command: dict[str, Any]) -> bool:
    return bool(
        isinstance(event, dict)
        and event.get("event_type") == "ArtefactRegistered"
        and all(
            event.get(key) == command.get(key)
            for key in (
                "command_id",
                "command_type",
                "actor_id",
                "authority_grant_id",
                "idempotency_key",
                "correlation_id",
                "causation_id",
                "project_id",
            )
        )
        and event.get("stream_id") == command.get("target_stream_id")
        and event.get("command_payload_hash") == sha256_hex(canonical_bytes(command.get("payload")))
        and event.get("payload") == command.get("payload")
    )


def _recovery_marker(command: dict[str, Any], relative_path: str, raw: bytes) -> dict[str, Any]:
    return {
        "schema_id": _REGISTRATION_RECOVERY_SCHEMA_ID,
        "schema_version": "1.0.0",
        "command": command,
        "relative_path": relative_path,
        "raw_base64": base64.b64encode(raw).decode("ascii"),
        "raw_sha256": sha256_hex(raw),
        "size_bytes": len(raw),
    }


def _publish_recovery_marker(control_root: Path, command: dict[str, Any], relative_path: str, raw: bytes) -> str:
    store = CandidateDocumentStore(control_root, relative_directory=_REGISTRATION_RECOVERY_DIRECTORY)
    return store.publish_bytes(
        str(command["command_id"]), canonical_bytes(_recovery_marker(command, relative_path, raw))
    )


def _remove_recovery_marker(control_root: Path, command_id: str) -> None:
    relative = (_REGISTRATION_RECOVERY_DIRECTORY / f"{command_id}.json").as_posix()
    try:
        with _open_existing_contained_file(control_root, relative) as (fd, target):
            identity = os.fstat(fd)
            os.close(fd)
    except FileNotFoundError:
        return
    _remove_created_file(target, identity)


def _is_abandoned_recovery_staging_file(path: Path) -> bool:
    """Recognize non-authoritative staging leaves left by a hard process stop."""

    name = path.name
    if not name.startswith(".") or not name.endswith(".tmp"):
        return False
    marker_name, separator, nonce = name[1:-4].rpartition(".")
    if not separator or not marker_name.endswith(".json") or len(nonce) != 32:
        return False
    return all(character in "0123456789abcdef" for character in nonce)


def recover_registered_content(control_root: Path, events: tuple[dict[str, Any], ...]) -> None:
    """Reconcile committed registrations with their exact pre-submit byte markers."""

    root = control_root.resolve(strict=True)
    directory = root / _REGISTRATION_RECOVERY_DIRECTORY
    try:
        metadata = directory.lstat()
    except FileNotFoundError:
        return
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    ):
        raise ConfigurationError("registration recovery directory is not physical")
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if _is_abandoned_recovery_staging_file(path):
            metadata = path.lstat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            ):
                raise IntegrityError("registration recovery directory contains an invalid staging entry")
            continue
        if path.suffix != ".json" or not path.is_file() or path.is_symlink():
            raise IntegrityError("registration recovery directory contains an invalid entry")
        relative_marker = path.relative_to(root).as_posix()
        raw_marker = _read_existing_contained_file(root, relative_marker)
        try:
            marker = json.loads(raw_marker)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("registration recovery marker is invalid") from exc
        if (
            not isinstance(marker, dict)
            or raw_marker != canonical_bytes(marker)
            or set(marker)
            != {
                "schema_id",
                "schema_version",
                "command",
                "relative_path",
                "raw_base64",
                "raw_sha256",
                "size_bytes",
            }
            or marker.get("schema_id") != _REGISTRATION_RECOVERY_SCHEMA_ID
            or marker.get("schema_version") != "1.0.0"
        ):
            raise IntegrityError("registration recovery marker is invalid")
        command = marker.get("command")
        relative_path = marker.get("relative_path")
        try:
            raw = base64.b64decode(marker.get("raw_base64"), validate=True)
        except (binascii.Error, TypeError, ValueError) as exc:
            raise IntegrityError("registration recovery marker bytes are invalid") from exc
        payload = command.get("payload") if isinstance(command, dict) else None
        manifest = payload.get("manifest") if isinstance(payload, dict) else None
        artefact_id = command.get("target_stream_id") if isinstance(command, dict) else None
        if (
            not isinstance(relative_path, str)
            or not isinstance(manifest, dict)
            or not isinstance(artefact_id, str)
            or path.name != f"{command.get('command_id')}.json"
            or payload.get("new_artefact_id") != artefact_id
            or manifest.get("artefact_id") != artefact_id
            or manifest.get("relative_path") != relative_path
            or Path(relative_path).stem != artefact_id
            or manifest.get("content_sha256") != marker.get("raw_sha256")
            or manifest.get("size_bytes") != marker.get("size_bytes")
            or len(raw) != marker.get("size_bytes")
            or sha256_hex(raw) != marker.get("raw_sha256")
        ):
            raise IntegrityError("registration recovery marker binding differs")
        matches = [event for event in events if _registration_event_matches(event, command)]
        competing = [
            event
            for event in events
            if event.get("event_type") == "ArtefactRegistered" and event.get("stream_id") == artefact_id
        ]
        if len(matches) > 1 or (not matches and competing):
            raise IntegrityError("registration recovery event binding differs")
        if not matches:
            continue
        _write_immutable_raw(root, relative_path, raw)
        _remove_recovery_marker(root, str(command["command_id"]))


def publish_registered_raw_content(
    *,
    repository_root: Path,
    publication: RawContentPublication,
    registration: CandidateRegistration,
    control_root: Path,
    command_service: CommandSubmitter,
) -> RegisteredCandidate:
    """Register then immutably publish one exact committed SPEC/methods markdown file.

    Registration precedes byte publication so an interruption cannot leave an
    unregistered file.  Exact retry replays the command and reconciles the
    missing immutable bytes, matching candidate-document recovery semantics.
    """

    prepared = prepare_registered_raw_content(
        repository_root=repository_root,
        publication=publication,
        registration=registration,
        control_root=control_root,
    )
    raw = prepared.raw_bytes
    command = prepared.command
    _publish_recovery_marker(control_root, command, publication.destination_relative_path, raw)
    receipt = command_service.submit(command)
    if getattr(receipt, "status", None) not in {"accepted", "replayed"}:
        _remove_recovery_marker(control_root, str(command["command_id"]))
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        raise ArsError(f"raw artefact registration was not accepted ({reason})")
    _write_immutable_raw(control_root, publication.destination_relative_path, raw)
    _remove_recovery_marker(control_root, str(command["command_id"]))
    return RegisteredCandidate(
        registration.artefact_id,
        publication.content_sha256,
        raw,
        publication.destination_relative_path,
        receipt,
    )


def prepare_registered_raw_content(
    *,
    repository_root: Path,
    publication: RawContentPublication,
    registration: CandidateRegistration,
    control_root: Path,
) -> PreparedRawRegistration:
    """Validate and derive one raw-content registration without publishing it."""

    raw = _validate_committed_raw_source(repository_root, publication)
    destination = Path(publication.destination_relative_path)
    expected_artefact_id = spec_brief_input_artefact_id(
        publication.source_relative_path,
        publication.content_sha256,
    )
    expected_destination = f"{_RAW_DESTINATION_PREFIX}{expected_artefact_id}.md"
    if (
        registration.artefact_id != expected_artefact_id
        or destination.stem != expected_artefact_id
        or publication.destination_relative_path != expected_destination
    ):
        raise ConfigurationError("raw content destination does not bind the artefact identity")
    _require_physical_destination(control_root, publication.destination_relative_path)
    try:
        existing = _read_existing_contained_file(control_root, publication.destination_relative_path)
    except FileNotFoundError:
        existing = None
    if existing is not None and existing != raw:
        raise ConflictError("raw content destination already binds different bytes")
    manifest = deepcopy(registration.manifest)
    if manifest.get("artefact_id") != registration.artefact_id:
        raise ArsError("registration manifest does not bind the raw artefact")
    manifest.update(
        {
            "root_id": "control",
            "relative_path": publication.destination_relative_path,
            "size_bytes": publication.size_bytes,
            "media_type": publication.media_type,
            "content_sha256": publication.content_sha256,
            "artefact_type": publication.document_type,
        }
    )
    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise ArsError("registration manifest authority is missing")
    authority["use_authority"] = "candidate"
    metadata_digest = sha256_hex(canonical_bytes(manifest))
    idempotency_key = f"methods-register-raw:{registration.artefact_id}:{metadata_digest}"
    command = {
        "command_id": _stable_command_id(idempotency_key),
        "command_type": "RegisterArtefact",
        "schema_id": "ars://core/command/RegisterArtefact",
        "schema_version": "1.0.0",
        "submitted_at": registration.submitted_at,
        "actor_id": registration.actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": registration.authority_grant_id,
        "target_stream_id": registration.artefact_id,
        "expected_stream_version": 0,
        "idempotency_key": idempotency_key,
        "correlation_id": registration.correlation_id,
        "causation_id": None,
        "reason": registration.reason,
        "evidence_refs": [],
        "payload": {"new_artefact_id": registration.artefact_id, "manifest": manifest},
        "project_id": registration.project_id,
    }
    return PreparedRawRegistration(registration, publication, raw, command)


def _stable_command_id(idempotency_key: str) -> str:
    """Derive one canonical UUIDv7 command identity for an exact registration."""
    value = int.from_bytes(hashlib.sha256(idempotency_key.encode("utf-8")).digest()[:16], "big")
    value = (value & ~(0xF << 76)) | (0x7 << 76)
    value = (value & ~(0b11 << 62)) | (0b10 << 62)
    return f"cmd_{uuid.UUID(int=value)}"


def register_candidate_document(
    *,
    value: dict[str, Any],
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
    command_service: CommandSubmitter,
) -> RegisteredCandidate:
    """Persist and register exact bytes, always forcing initial candidate authority."""
    prepared = prepare_candidate_document(
        value=value,
        registration=registration,
        document_store=document_store,
    )
    _publish_recovery_marker(
        document_store.control_root,
        prepared.command,
        prepared.relative_path,
        prepared.raw_bytes,
    )
    receipt = command_service.submit(prepared.command)
    if getattr(receipt, "status", None) not in {"accepted", "replayed"}:
        _remove_recovery_marker(document_store.control_root, str(prepared.command["command_id"]))
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        explanation = getattr(receipt, "explanation", None)
        detail = f": {explanation}" if explanation else ""
        raise ArsError(f"candidate artefact registration was not accepted ({reason}){detail}")
    document_store.write(registration.artefact_id, prepared.raw_bytes)
    _remove_recovery_marker(document_store.control_root, str(prepared.command["command_id"]))
    return RegisteredCandidate(
        registration.artefact_id,
        prepared.content_sha256,
        prepared.raw_bytes,
        prepared.relative_path,
        receipt,
    )


def prepare_candidate_document(
    *,
    value: dict[str, Any],
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
) -> PreparedCandidateRegistration:
    """Derive one candidate-document registration without publishing it."""

    raw = canonical_bytes(value)
    digest = sha256_hex(raw)
    relative_path = document_store.relative_path(registration.artefact_id)
    _require_physical_destination(document_store.control_root, relative_path)
    manifest = deepcopy(registration.manifest)
    if manifest.get("artefact_id") != registration.artefact_id:
        raise ArsError("registration manifest does not bind the document artefact")
    manifest.update(
        {
            "root_id": document_store.root_id,
            "relative_path": relative_path,
            "size_bytes": len(raw),
            "media_type": "application/json",
            "content_sha256": digest,
        }
    )
    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise ArsError("registration manifest authority is missing")
    authority["use_authority"] = "candidate"
    idempotency_key = f"methods-register:{registration.artefact_id}:{digest}"
    command = {
        "command_id": _stable_command_id(idempotency_key),
        "command_type": "RegisterArtefact",
        "schema_id": "ars://core/command/RegisterArtefact",
        "schema_version": "1.0.0",
        "submitted_at": registration.submitted_at,
        "actor_id": registration.actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": registration.authority_grant_id,
        "target_stream_id": registration.artefact_id,
        "expected_stream_version": 0,
        "idempotency_key": idempotency_key,
        "correlation_id": registration.correlation_id,
        "causation_id": None,
        "reason": registration.reason,
        "evidence_refs": [],
        "payload": {"new_artefact_id": registration.artefact_id, "manifest": manifest},
        "project_id": registration.project_id,
    }
    return PreparedCandidateRegistration(value, registration, raw, digest, relative_path, command)


__all__ = [
    "CandidateDocumentStore",
    "CandidateRegistration",
    "PreparedRawRegistration",
    "PreparedCandidateRegistration",
    "CommandSubmitter",
    "RawContentPublication",
    "RegisteredCandidate",
    "publish_registered_raw_content",
    "prepare_registered_raw_content",
    "prepare_candidate_document",
    "recover_registered_content",
    "register_candidate_document",
    "spec_brief_input_artefact_id",
]
