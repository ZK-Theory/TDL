"""Exact worktree-file provenance against one committed Git subject."""

from __future__ import annotations

import os
import stat
import tarfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterator

from research_system.errors import ConfigurationError, IntegrityError
from research_system.git_execution import run_git


def _after_committed_parent_held(_repository_root: Path, _relative_path: Path) -> None:
    """Deterministic test seam before the leaf is opened."""


def _after_committed_file_opened(_repository_root: Path, _relative_path: Path) -> None:
    """Deterministic test seam after the physical leaf is open."""


def _hold_windows_directories(paths: list[Path], *, label: str) -> list[int]:
    """Hold physical directories without delete sharing."""

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
    invalid = ctypes.c_void_p(-1).value
    handles: list[int] = []
    flags = 0x02000000 | 0x00200000  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
    try:
        for path in paths:
            handle = create_file(
                str(path),
                0x0001 | 0x0080 | 0x00100000,  # LIST_DIRECTORY | READ_ATTRIBUTES | SYNCHRONIZE
                0x1 | 0x2,  # share read/write, but never delete
                None,
                3,  # OPEN_EXISTING
                flags,
                None,
            )
            if handle == invalid:
                raise OSError(ctypes.get_last_error(), f"{label} parent is unavailable")
            handles.append(int(handle))
            metadata = path.lstat()
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0) & 0x400
            ):
                raise IntegrityError(f"{label} parent is not a physical directory")
        return handles
    except Exception:
        close_handle = kernel32.CloseHandle
        for handle in reversed(handles):
            close_handle(ctypes.c_void_p(handle))
        raise


def _open_windows_relative_file(parent_handle: int, name: str, *, label: str) -> int:
    """Open one non-reparse leaf relative to a held Windows directory."""

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
        0x40,
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
    status = nt_create_file(
        ctypes.byref(native_handle),
        0x80000000 | 0x00000080 | 0x00100000,
        ctypes.byref(attributes),
        ctypes.byref(status_block),
        None,
        0,
        0x1,
        1,
        0x40 | 0x20 | 0x00200000,
        None,
        0,
    )
    if status < 0 or not native_handle.value:
        raise OSError(status, f"{label} leaf could not be opened")
    try:
        return msvcrt.open_osfhandle(native_handle.value, os.O_RDONLY | os.O_BINARY)
    except Exception:
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(native_handle)
        raise


@contextmanager
def _held_parent(repository_root: Path, relative_path: Path, *, label: str) -> Iterator[tuple[int, tuple[int, ...]]]:
    """Hold every physical directory component through the file read."""

    descriptors: list[int] = []
    windows_handles: list[int] = []
    try:
        if os.open in os.supports_dir_fd and hasattr(os, "O_DIRECTORY"):
            flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
            descriptors.append(os.open(repository_root, flags))
            for part in relative_path.parts[:-1]:
                descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
            yield descriptors[-1], tuple(descriptors)
        elif os.name == "nt":
            parents = [repository_root]
            for part in relative_path.parts[:-1]:
                parents.append(parents[-1] / part)
            windows_handles = _hold_windows_directories(parents, label=label)
            yield windows_handles[-1], ()
        else:
            raise ConfigurationError(f"{label} physical held read is unsupported on this platform")
    except OSError as exc:
        raise IntegrityError(f"{label} physical parent is unavailable") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        if windows_handles:
            import ctypes

            close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
            for handle in reversed(windows_handles):
                close_handle(ctypes.c_void_p(handle))


def _validate_posix_chain(
    repository_root: Path,
    relative_path: Path,
    directory_descriptors: tuple[int, ...],
    opened: os.stat_result,
    *,
    label: str,
) -> None:
    """Prove the lexical chain still names the held directories and leaf."""

    current = repository_root
    for part, descriptor in zip((None, *relative_path.parts[:-1]), directory_descriptors, strict=True):
        if part is not None:
            current /= part
        metadata = current.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or not os.path.samestat(metadata, os.fstat(descriptor))
        ):
            raise IntegrityError(f"{label} parent changed during read")
    leaf = (repository_root / relative_path).lstat()
    if not os.path.samestat(leaf, opened) or stat.S_ISLNK(leaf.st_mode):
        raise IntegrityError(f"{label} changed during read")


def _validate_relative_path(relative_path: Path, *, label: str) -> None:
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or ".." in relative_path.parts
        or relative_path.as_posix() != str(relative_path).replace("\\", "/")
    ):
        raise IntegrityError(f"{label} path is not canonical")


def _resolved_repository_root(repository_root: Path, *, label: str) -> Path:
    try:
        root = repository_root.resolve(strict=True)
    except OSError as exc:
        raise IntegrityError(f"{label} repository root is unavailable") from exc
    if root != repository_root:
        raise IntegrityError(f"{label} repository root is redirected")
    return root


def _committed_blob_bytes(root: Path, relative_path: Path, *, label: str, commit: str) -> bytes:
    listing = run_git(
        root,
        "ls-tree",
        "-z",
        commit,
        "--",
        relative_path.as_posix(),
        text=False,
        unavailable_message=f"{label} Git inspection timed out or is unavailable",
    )
    if listing.returncode != 0:
        stderr = listing.stderr.decode("utf-8", errors="replace").strip()
        raise ConfigurationError(f"{label} Git inspection failed: {stderr}")
    entries = bytes(listing.stdout).split(b"\0")
    if entries and entries[-1] == b"":
        entries.pop()
    expected_path = relative_path.as_posix().encode("utf-8")
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ConfigurationError(f"{label} is absent from the exact Git subject")
    header, listed_path = entries[0].split(b"\t", 1)
    header_fields = header.split(b" ")
    if len(header_fields) != 3 or header_fields[1] != b"blob" or listed_path != expected_path:
        raise ConfigurationError(f"{label} is not one exact committed blob")
    try:
        object_id = header_fields[2].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ConfigurationError(f"{label} Git object identity is invalid") from exc
    committed = run_git(
        root,
        "cat-file",
        "blob",
        object_id,
        text=False,
        unavailable_message=f"{label} Git inspection timed out or is unavailable",
    )
    if committed.returncode != 0:
        stderr = committed.stderr.decode("utf-8", errors="replace").strip()
        raise ConfigurationError(f"{label} Git inspection failed: {stderr}")
    return bytes(committed.stdout)


def _read_physical_file_against_bytes(
    root: Path,
    relative_path: Path,
    committed_raw: bytes,
    *,
    label: str,
) -> bytes:
    """Read one held physical file against bytes already derived by this module."""

    with _held_parent(root, relative_path, label=label) as (parent, directory_descriptors):
        try:
            _after_committed_parent_held(root, relative_path)
            if os.name == "nt" and not directory_descriptors:
                descriptor = _open_windows_relative_file(parent, relative_path.name, label=label)
            else:
                descriptor = os.open(
                    relative_path.name,
                    os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent,
                )
        except OSError as exc:
            if directory_descriptors:
                try:
                    linked = os.stat(relative_path.name, dir_fd=parent, follow_symlinks=False)
                except OSError:
                    linked = None
                if linked is not None and stat.S_ISLNK(linked.st_mode):
                    raise IntegrityError(f"{label} path is redirected") from exc
            raise IntegrityError(f"{label} physical file is unavailable") from exc
        try:
            opened = os.fstat(descriptor)
            reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            if stat.S_ISLNK(opened.st_mode) or getattr(opened, "st_file_attributes", 0) & reparse:
                raise IntegrityError(f"{label} path is redirected")
            if not stat.S_ISREG(opened.st_mode):
                raise IntegrityError(f"{label} is not a repository-owned physical regular file")
            _after_committed_file_opened(root, relative_path)
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                raw = handle.read()
            if directory_descriptors:
                _validate_posix_chain(root, relative_path, directory_descriptors, opened, label=label)
        except OSError as exc:
            raise IntegrityError(f"{label} changed during read") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if raw != committed_raw:
            raise IntegrityError(f"{label} differs from the exact Git subject")
        return raw


def read_exact_committed_physical_file(
    repository_root: Path,
    relative_path: Path,
    *,
    label: str,
    commit: str = "HEAD",
) -> bytes:
    """Read one held physical file only when its bytes match Git."""

    _validate_relative_path(relative_path, label=label)
    root = _resolved_repository_root(repository_root, label=label)
    committed_raw = _committed_blob_bytes(root, relative_path, label=label, commit=commit)
    return _read_physical_file_against_bytes(root, relative_path, committed_raw, label=label)


def read_exact_committed_physical_tree(
    repository_root: Path,
    relative_root: Path,
    *,
    suffix: str,
    label: str,
    commit: str = "HEAD",
) -> tuple[tuple[str, bytes], ...]:
    """Read an exact committed subtree with one Git snapshot operation."""

    _validate_relative_path(relative_root, label=label)
    if not suffix or Path(suffix).name != suffix:
        raise IntegrityError(f"{label} suffix is invalid")
    root = _resolved_repository_root(repository_root, label=label)
    archive = run_git(
        root,
        "archive",
        "--format=tar",
        commit,
        "--",
        relative_root.as_posix(),
        text=False,
        unavailable_message=f"{label} Git inspection timed out or is unavailable",
    )
    if archive.returncode != 0:
        stderr = archive.stderr.decode("utf-8", errors="replace").strip()
        raise ConfigurationError(f"{label} Git inspection failed: {stderr}")
    committed: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=BytesIO(bytes(archive.stdout)), mode="r:") as bundle:
            for member in bundle.getmembers():
                member_path = Path(member.name)
                if not member_path.name.endswith(suffix):
                    continue
                if member_path.is_absolute() or ".." in member_path.parts or not member.isfile():
                    raise IntegrityError(f"{label} contains a non-regular physical path")
                relative = member_path.relative_to(relative_root).as_posix()
                if relative in committed:
                    raise IntegrityError(f"{label} contains a duplicate file")
                handle = bundle.extractfile(member)
                if handle is None:
                    raise IntegrityError(f"{label} contains an unreadable file")
                committed[relative] = handle.read()
    except (tarfile.TarError, OSError, ValueError) as exc:
        raise IntegrityError(f"{label} Git archive is invalid") from exc

    physical_root = root / relative_root
    try:
        metadata = physical_root.lstat()
    except OSError as exc:
        raise IntegrityError(f"{label} physical root is unavailable") from exc
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0) & reparse
    ):
        raise IntegrityError(f"{label} physical root is redirected")
    physical_paths = sorted(physical_root.rglob(f"*{suffix}"), key=lambda item: item.as_posix())
    physical_relatives = {path.relative_to(physical_root).as_posix() for path in physical_paths}
    if not committed or physical_relatives != set(committed):
        raise IntegrityError(f"{label} differs from the exact Git subject")
    return tuple(
        (
            path.relative_to(physical_root).as_posix(),
            _read_physical_file_against_bytes(
                root,
                path.relative_to(root),
                committed[path.relative_to(physical_root).as_posix()],
                label=f"{label} file",
            ),
        )
        for path in physical_paths
    )


__all__ = ["read_exact_committed_physical_file", "read_exact_committed_physical_tree"]
