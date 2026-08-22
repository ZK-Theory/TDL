"""Physical, descriptor-held publication for control-root contained files.

The control store has immutable evidence leaves and a small number of governed
mutable leaves.  Both need the same protections: every path component must be
physical, the parent used for the final directory operation must remain held,
and cleanup must never unlink a name claimed by another writer.
"""

from __future__ import annotations

import hashlib
import os
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from research_system.errors import ConfigurationError, ConflictError, IntegrityError
from research_system.store.durability import fsync_directory


def _require_physical_destination(control_root: Path, relative_path: str, *, create: bool = False) -> Path:
    root = control_root.resolve(strict=True)
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        raise ConfigurationError("contained-file destination is not canonical and control-relative")
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
                raise ConfigurationError("contained-file destination parent is unavailable") from exc
        except OSError as exc:
            raise ConfigurationError("contained-file destination parent is unavailable") from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & reparse
        ):
            raise ConfigurationError("contained-file destination parent is not a physical directory")
    target = current / relative.name
    if not missing_parent and (target.exists() or target.is_symlink()):
        try:
            metadata = target.lstat()
        except OSError as exc:
            raise ConfigurationError("contained-file destination is unavailable") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & reparse
        ):
            raise ConfigurationError("contained-file destination is not a physical regular file")
    return target


def validate_contained_destination(control_root: Path, relative_path: str) -> Path:
    """Validate a contained path without creating parents or publishing bytes."""

    return _require_physical_destination(control_root, relative_path)


def _hold_windows_directories(paths: list[Path], *, allow_outer_delete_protection: bool) -> list[int]:
    """Hold physical directory handles without delete sharing during leaf operations."""

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
    file_share_delete = 0x4
    handles: list[int] = []
    flags = 0x02000000 | 0x00200000  # FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT
    try:
        for path in paths:
            desired_access = 0x0001 | 0x0080 | 0x00100000  # LIST_DIRECTORY | READ_ATTRIBUTES | SYNCHRONIZE
            handle = create_file(str(path), desired_access, 0x1 | 0x2, None, 3, flags, None)
            if handle == invalid and ctypes.get_last_error() == 32:
                from research_system.store.lock import has_live_delete_protected_directory_anchor

                # Only an exact live anchor held by this thread can justify
                # delete sharing. A foreign sharing violation is not proof of
                # the surrounding writer-lock invariant.
                if has_live_delete_protected_directory_anchor(path):
                    handle = create_file(
                        str(path),
                        desired_access,
                        0x1 | 0x2 | file_share_delete,
                        None,
                        3,
                        flags,
                        None,
                    )
            if handle == invalid:
                raise OSError(ctypes.get_last_error(), "physical destination directory is unavailable")
            handles.append(int(handle))
            metadata = path.lstat()
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0) & 0x400
            ):
                raise ConfigurationError("contained-file destination parent is not a physical directory")
        return handles
    except Exception:
        for handle in reversed(handles):
            close_handle(ctypes.c_void_p(handle))
        raise


def _open_windows_relative_file(
    parent_handle: int,
    name: str,
    *,
    create: bool,
) -> int:
    """Open a leaf relative to a held Windows directory without following reparses."""

    import ctypes
    import msvcrt

    class UnicodeString(ctypes.Structure):
        _fields_ = (
            ("Length", ctypes.c_ushort),
            ("MaximumLength", ctypes.c_ushort),
            ("Buffer", ctypes.c_wchar_p),
        )

    class IoStatusBlock(ctypes.Structure):
        _fields_ = (("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t))

    class ObjectAttributes(ctypes.Structure):
        _fields_ = (
            ("Length", ctypes.c_ulong),
            ("RootDirectory", ctypes.c_void_p),
            ("ObjectName", ctypes.POINTER(UnicodeString)),
            ("Attributes", ctypes.c_ulong),
            ("SecurityDescriptor", ctypes.c_void_p),
            ("SecurityQualityOfService", ctypes.c_void_p),
        )

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
        0x80 if create else 0,
        0x1,
        2 if create else 1,
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
        raise OSError(status, f"contained-file destination leaf could not be {operation}")
    try:
        access = os.O_WRONLY if create else os.O_RDONLY
        return msvcrt.open_osfhandle(native_handle.value, access | os.O_BINARY)
    except Exception:
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(native_handle)
        raise


def _open_windows_relative_new_file(parent_handle: int, name: str) -> int:
    return _open_windows_relative_file(parent_handle, name, create=True)


def _open_windows_relative_existing_file(parent_handle: int, name: str) -> int:
    return _open_windows_relative_file(parent_handle, name, create=False)


@contextmanager
def _hold_contained_parent(
    control_root: Path,
    relative_path: str,
    *,
    create: bool,
    allow_outer_delete_protection: bool = False,
) -> Iterator[tuple[int, Path]]:
    """Hold the verified parent used for a relative atomic directory operation."""

    target = _require_physical_destination(control_root, relative_path, create=create)
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
            windows_handles = _hold_windows_directories(
                parents,
                allow_outer_delete_protection=allow_outer_delete_protection,
            )
            yield windows_handles[-1], target
        else:
            raise ConfigurationError("atomic contained-file operation is unsupported on this platform")
    finally:
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)
        if windows_handles:
            import ctypes

            close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
            for handle in reversed(windows_handles):
                close_handle(ctypes.c_void_p(handle))


def _after_contained_file_fsync(_temporary: Path, _target: Path) -> None:
    """Test seam after staging is durable but before final-name publication."""


def _after_contained_file_linked(_temporary: Path, _target: Path) -> None:
    """Test seam after an immutable final link exists but before verification."""


def _after_contained_file_predecessor_verified(_temporary: Path, _target: Path) -> None:
    """Test seam after an exact predecessor is verified but before replacement."""


def _after_contained_file_predecessor_removed(_temporary: Path, _target: Path) -> None:
    """Test seam after the exact predecessor name is absent before successor publication."""


def _after_contained_file_replacement_staged(_temporary: Path, _target: Path) -> None:
    """Test seam after a deterministic replacement stage is durable."""


def _after_contained_file_predecessor_backed_up(_temporary: Path, _target: Path) -> None:
    """Test seam after an exact predecessor backup is durable."""


def _after_contained_file_successor_linked(_temporary: Path, _target: Path) -> None:
    """Test seam after successor publication but before attempt cleanup."""


def _link_held_contained_file(
    parent_descriptor: int,
    held_target: Path,
    source_name: str,
    destination_name: str,
) -> None:
    """Create one no-replace hard link wholly within the held physical parent."""

    if os.name == "nt":
        os.link(
            held_target.with_name(source_name),
            held_target.with_name(destination_name),
            follow_symlinks=False,
        )
    else:
        os.link(
            source_name,
            destination_name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
            follow_symlinks=False,
        )


def _read_optional_held_contained_file(
    parent_descriptor: int,
    held_target: Path,
    name: str,
) -> tuple[bytes, os.stat_result] | None:
    try:
        return _read_held_contained_file(parent_descriptor, held_target, name)
    except FileNotFoundError:
        return None


def _write_held_contained_stage(
    parent_descriptor: int,
    held_target: Path,
    name: str,
    data: bytes,
) -> os.stat_result:
    """Create and durably write one new stage under the already-held parent."""

    if os.name == "nt":
        descriptor = _open_windows_relative_new_file(parent_descriptor, name)
    else:
        descriptor = os.open(
            name,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_descriptor,
        )
    with os.fdopen(descriptor, "wb") as handle:
        identity = os.fstat(handle.fileno())
        if not stat.S_ISREG(identity.st_mode):
            raise ConfigurationError("contained-file replacement staging is not a physical regular file")
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if os.name == "nt":
        fsync_directory(held_target.parent)
    else:
        os.fsync(parent_descriptor)
    return identity


def _held_parent_matches_destination(parent_descriptor: int, held_target: Path) -> None:
    """Reject a POSIX pathname redirect after the destination parent was opened."""

    if os.name == "nt":
        # The held directory handle excludes delete sharing, so this parent
        # cannot be renamed or replaced while its relative operation runs.
        return
    try:
        current_parent = held_target.parent.lstat()
    except OSError as exc:
        raise IntegrityError("contained-file destination parent changed while held") from exc
    held_parent = os.fstat(parent_descriptor)
    if (
        not stat.S_ISDIR(current_parent.st_mode)
        or stat.S_ISLNK(current_parent.st_mode)
        or not os.path.samestat(held_parent, current_parent)
    ):
        raise IntegrityError("contained-file destination parent changed while held")


def _held_contained_file_identity(parent_descriptor: int, held_target: Path, name: str) -> os.stat_result:
    """Read one physical leaf identity relative to the held parent directory."""

    if os.name == "nt":
        identity = held_target.with_name(name).lstat()
    else:
        identity = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if (
        not stat.S_ISREG(identity.st_mode)
        or stat.S_ISLNK(identity.st_mode)
        or getattr(identity, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    ):
        raise ConfigurationError("contained-file destination is not a physical regular file")
    return identity


def _read_held_contained_file(parent_descriptor: int, held_target: Path, name: str) -> tuple[bytes, os.stat_result]:
    """Read one physical leaf relative to the held parent and return its identity."""

    if os.name == "nt":
        descriptor = _open_windows_relative_existing_file(parent_descriptor, name)
    else:
        descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_descriptor)
    try:
        identity = os.fstat(descriptor)
        if (
            not stat.S_ISREG(identity.st_mode)
            or stat.S_ISLNK(identity.st_mode)
            or getattr(identity, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ConfigurationError("contained-file destination is not a physical regular file")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            return handle.read(), identity
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _remove_held_created_file(
    parent_descriptor: int,
    held_target: Path,
    name: str,
    identity: os.stat_result,
) -> bool:
    """Remove one attempt-owned leaf while its verified parent remains held."""

    try:
        current = _held_contained_file_identity(parent_descriptor, held_target, name)
    except (ConfigurationError, OSError):
        return False
    if not os.path.samestat(current, identity):
        return False
    try:
        if os.name == "nt":
            held_target.with_name(name).unlink()
        else:
            os.unlink(name, dir_fd=parent_descriptor)
    except OSError:
        return False
    try:
        if os.name == "nt":
            fsync_directory(held_target.parent)
        else:
            os.fsync(parent_descriptor)
    except OSError:
        pass
    return True


def _remove_created_file(target: Path, identity: os.stat_result) -> None:
    """Fallback cleanup that only removes the exact staging leaf this attempt opened."""

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


@contextmanager
def _open_new_contained_file(
    control_root: Path,
    relative_path: str,
    *,
    allow_outer_delete_protection: bool = False,
) -> Iterator[tuple[int, Path]]:
    """Create one fresh leaf while its trusted parent chain remains bound."""

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
            windows_handles = _hold_windows_directories(
                parents,
                allow_outer_delete_protection=allow_outer_delete_protection,
            )
            descriptor = _open_windows_relative_new_file(windows_handles[-1], relative.name)
        else:
            raise ConfigurationError("atomic contained-file creation is unsupported on this platform")
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
def _open_existing_contained_file(
    control_root: Path,
    relative_path: str,
    *,
    allow_outer_delete_protection: bool = False,
) -> Iterator[tuple[int, Path]]:
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
                relative.name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_descriptors[-1]
            )
        elif os.name == "nt":
            parents = [root]
            for part in relative.parts[:-1]:
                parents.append(parents[-1] / part)
            windows_handles = _hold_windows_directories(
                parents,
                allow_outer_delete_protection=allow_outer_delete_protection,
            )
            descriptor = _open_windows_relative_existing_file(windows_handles[-1], relative.name)
        else:
            raise ConfigurationError("atomic contained-file reading is unsupported on this platform")
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ConfigurationError("contained-file destination is not a physical regular file")
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


def read_contained_file(
    control_root: Path,
    relative_path: str,
    *,
    allow_outer_delete_protection: bool = False,
) -> bytes:
    """Read one existing physical leaf through a descriptor-held parent chain."""

    with _open_existing_contained_file(
        control_root,
        relative_path,
        allow_outer_delete_protection=allow_outer_delete_protection,
    ) as (descriptor, _target):
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read()


def read_contained_directory_files(
    control_root: Path,
    relative_directory: str,
    *,
    suffix: str,
    allow_outer_delete_protection: bool = False,
) -> tuple[tuple[str, bytes], ...]:
    """Read matching physical leaves while retaining one verified parent."""

    relative = Path(relative_directory)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_directory:
        raise ConfigurationError("contained-file directory is not canonical and control-relative")
    if not suffix or Path(suffix).name != suffix:
        raise ConfigurationError("contained-file directory suffix is invalid")
    directory = control_root.resolve(strict=True) / relative
    try:
        directory.lstat()
    except FileNotFoundError:
        return ()
    sentinel = (relative / ".directory-snapshot").as_posix()
    try:
        with _hold_contained_parent(
            control_root,
            sentinel,
            create=False,
            allow_outer_delete_protection=allow_outer_delete_protection,
        ) as (parent_descriptor, held_target):
            names = os.listdir(held_target.parent if os.name == "nt" else parent_descriptor)
            rows: list[tuple[str, bytes]] = []
            for name in sorted(names):
                if not name.endswith(suffix):
                    continue
                if not name or Path(name).name != name:
                    raise IntegrityError("contained-file directory returned an invalid leaf name")
                try:
                    data, _identity = _read_held_contained_file(parent_descriptor, held_target, name)
                except FileNotFoundError as exc:
                    raise IntegrityError("contained-file directory changed while held") from exc
                except OSError as exc:
                    raise ConfigurationError("contained-file directory has a non-physical leaf") from exc
                rows.append((name, data))
            _held_parent_matches_destination(parent_descriptor, held_target)
            return tuple(rows)
    except FileNotFoundError as exc:
        raise IntegrityError("contained-file directory changed while held") from exc


def publish_contained_exact_no_replace(
    control_root: Path,
    relative_path: str,
    data: bytes,
    *,
    conflict_message: str,
    allow_outer_delete_protection: bool = False,
) -> Path:
    """Durably publish exact bytes without replacing a competing final leaf."""

    relative = Path(relative_path)
    temporary_relative = relative.with_name(f".{relative.name}.{uuid.uuid4().hex}.tmp")
    temporary_target = control_root.resolve(strict=True) / temporary_relative
    temporary_identity: os.stat_result | None = None
    cleanup_staging = True
    final_target: Path | None = None
    try:
        with _open_new_contained_file(
            control_root,
            temporary_relative.as_posix(),
            allow_outer_delete_protection=allow_outer_delete_protection,
        ) as (descriptor, opened_target):
            temporary_target = opened_target
            with os.fdopen(descriptor, "wb") as handle:
                temporary_identity = os.fstat(handle.fileno())
                if not stat.S_ISREG(temporary_identity.st_mode):
                    raise ConfigurationError("contained-file staging destination is not a physical regular file")
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
                _after_contained_file_fsync(temporary_target, control_root / relative)
                with _hold_contained_parent(
                    control_root,
                    relative_path,
                    create=True,
                    allow_outer_delete_protection=allow_outer_delete_protection,
                ) as (
                    parent_descriptor,
                    held_target,
                ):
                    temporary_name = temporary_relative.name
                    final_link_created = False
                    cleanup_final_link = False
                    try:
                        try:
                            source_identity = (
                                temporary_target.lstat()
                                if os.name == "nt"
                                else _held_contained_file_identity(parent_descriptor, held_target, temporary_name)
                            )
                            if not os.path.samestat(temporary_identity, source_identity):
                                raise IntegrityError("contained-file staging identity changed before finalization")
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
                            existing, _identity = _read_held_contained_file(
                                parent_descriptor, held_target, relative.name
                            )
                            if existing != data:
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
                                    raise IntegrityError("published file identity differs from held staging file")
                            except (ConfigurationError, FileNotFoundError, IntegrityError, OSError):
                                cleanup_final_link = final_link_created
                                raise
                        _held_parent_matches_destination(parent_descriptor, held_target)
                        if os.name != "nt":
                            os.fsync(parent_descriptor)
                        else:
                            fsync_directory(held_target.parent)
                        final_target = held_target
                    except BaseException as exc:
                        if not isinstance(exc, Exception):
                            cleanup_staging = False
                        raise
                    finally:
                        if cleanup_staging:
                            if cleanup_final_link:
                                _remove_held_created_file(
                                    parent_descriptor,
                                    held_target,
                                    relative.name,
                                    temporary_identity,
                                )
                            cleanup_staging = not _remove_held_created_file(
                                parent_descriptor,
                                held_target,
                                temporary_name,
                                temporary_identity,
                            )
    except BaseException as exc:
        if not isinstance(exc, Exception):
            cleanup_staging = False
        if temporary_identity is not None and cleanup_staging:
            _remove_created_file(temporary_target, temporary_identity)
        raise
    finally:
        if cleanup_staging and temporary_identity is not None:
            _remove_created_file(temporary_target, temporary_identity)
    if final_target is None:
        raise IntegrityError("contained-file publication did not resolve a final destination")
    return final_target


def replace_contained_exact_predecessor(
    control_root: Path,
    relative_path: str,
    data: bytes,
    *,
    expected: bytes,
    conflict_message: str,
) -> Path:
    """Resumably advance one exact predecessor without overwriting a final leaf.

    The deterministic stage and backup names bind this operation to successor
    and predecessor bytes.  A retry can therefore recognize a hard-stop state
    before, during, or after the no-replace final-name transition.  It accepts
    only physical regular leaves with the expected bytes and hard-link
    identities; unknown leaves fail closed.
    """

    relative = Path(relative_path)
    successor_hash = hashlib.sha256(data).hexdigest()
    predecessor_hash = hashlib.sha256(expected).hexdigest()
    stage_name = f".{relative.name}.{successor_hash}.replace"
    backup_name = f".{relative.name}.{predecessor_hash}.previous"

    with _hold_contained_parent(control_root, relative_path, create=False) as (parent_descriptor, held_target):
        stage_target = held_target.with_name(stage_name)

        def state(name: str) -> tuple[bytes, os.stat_result] | None:
            return _read_optional_held_contained_file(parent_descriptor, held_target, name)

        def remove_exact(name: str, identity: os.stat_result) -> bool:
            return _remove_held_created_file(parent_descriptor, held_target, name, identity)

        final_state = state(relative.name)
        stage_state = state(stage_name)
        backup_state = state(backup_name)
        if stage_state is not None and stage_state[0] != data:
            raise ConflictError(conflict_message)
        if backup_state is not None and backup_state[0] != expected:
            raise ConflictError(conflict_message)

        if final_state is not None and final_state[0] == data:
            # The successor was linked before a hard stop.  A same-inode stage
            # proves ownership; the deterministic exact predecessor backup is
            # then safe to discard as the completed attempt's residue.
            if stage_state is not None and os.path.samestat(stage_state[1], final_state[1]):
                remove_exact(stage_name, stage_state[1])
            if backup_state is not None:
                remove_exact(backup_name, backup_state[1])
            return held_target
        if final_state is not None and final_state[0] != expected:
            raise ConflictError(conflict_message)

        if stage_state is None:
            try:
                stage_identity = _write_held_contained_stage(parent_descriptor, held_target, stage_name, data)
            except FileExistsError:
                stage_state = state(stage_name)
                if stage_state is None or stage_state[0] != data:
                    raise ConflictError(conflict_message) from None
                stage_identity = stage_state[1]
            else:
                _after_contained_file_replacement_staged(stage_target, held_target)
        else:
            stage_identity = stage_state[1]

        if final_state is None:
            if backup_state is None:
                raise ConflictError(conflict_message)
            try:
                _link_held_contained_file(parent_descriptor, held_target, backup_name, relative.name)
            except FileExistsError:
                raise ConflictError(conflict_message) from None
            restored = state(relative.name)
            if restored is None or restored[0] != expected or not os.path.samestat(restored[1], backup_state[1]):
                raise IntegrityError("contained-file predecessor restoration is not exact")
            final_state = restored

        if backup_state is None:
            try:
                _link_held_contained_file(parent_descriptor, held_target, relative.name, backup_name)
            except FileExistsError:
                backup_state = state(backup_name)
                if backup_state is None or backup_state[0] != expected:
                    raise ConflictError(conflict_message) from None
            else:
                backup_state = state(backup_name)
                if backup_state is None:
                    raise IntegrityError("contained-file predecessor backup is unavailable")
                _after_contained_file_predecessor_backed_up(stage_target, held_target)

        if final_state is None or backup_state is None or not os.path.samestat(final_state[1], backup_state[1]):
            raise IntegrityError("contained-file predecessor backup identity is not exact")
        _after_contained_file_predecessor_verified(stage_target, held_target)
        current = state(relative.name)
        if current is None or current[0] != expected or not os.path.samestat(current[1], backup_state[1]):
            raise ConflictError(conflict_message)
        _held_parent_matches_destination(parent_descriptor, held_target)

        predecessor_removed = False
        try:
            if not remove_exact(relative.name, current[1]):
                raise ConflictError(conflict_message)
            predecessor_removed = True
            _after_contained_file_predecessor_removed(stage_target, held_target)
            try:
                _link_held_contained_file(parent_descriptor, held_target, stage_name, relative.name)
            except FileExistsError:
                raise ConflictError(conflict_message) from None
            successor = state(relative.name)
            if successor is None or successor[0] != data or not os.path.samestat(successor[1], stage_identity):
                raise IntegrityError("contained-file replacement identity is not exact")
            _after_contained_file_successor_linked(stage_target, held_target)
            if os.name == "nt":
                fsync_directory(held_target.parent)
            else:
                os.fsync(parent_descriptor)
            if not remove_exact(stage_name, stage_identity):
                raise IntegrityError("contained-file successor staging cleanup is unavailable")
            if not remove_exact(backup_name, backup_state[1]):
                raise IntegrityError("contained-file predecessor backup cleanup is unavailable")
            return held_target
        except BaseException as exc:
            if not isinstance(exc, Exception):
                raise
            if predecessor_removed and state(relative.name) is None:
                try:
                    _link_held_contained_file(parent_descriptor, held_target, backup_name, relative.name)
                except FileExistsError:
                    pass
            current_final = state(relative.name)
            if current_final is not None:
                current_stage = state(stage_name)
                if current_stage is not None and current_stage[0] == data:
                    remove_exact(stage_name, current_stage[1])
                current_backup = state(backup_name)
                if current_backup is not None and current_backup[0] == expected:
                    remove_exact(backup_name, current_backup[1])
            raise


def remove_contained_exact(
    control_root: Path,
    relative_path: str,
    *,
    expected: bytes,
    conflict_message: str,
    allow_outer_delete_protection: bool = False,
) -> bool:
    """Remove an exact leaf only while its physical parent and identity remain held."""

    try:
        with _hold_contained_parent(
            control_root,
            relative_path,
            create=False,
            allow_outer_delete_protection=allow_outer_delete_protection,
        ) as (parent_descriptor, held_target):
            try:
                actual, identity = _read_held_contained_file(parent_descriptor, held_target, Path(relative_path).name)
            except FileNotFoundError:
                return False
            if actual != expected:
                raise ConflictError(conflict_message)
            _held_parent_matches_destination(parent_descriptor, held_target)
            if not _remove_held_created_file(parent_descriptor, held_target, Path(relative_path).name, identity):
                raise ConflictError(conflict_message)
            return True
    except FileNotFoundError:
        return False
