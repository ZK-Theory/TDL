"""Physical containment checks for repository and control-store documents."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from research_system.errors import IntegrityError


def contained_regular_file(root: Path, relative_path: object, *, label: str) -> Path:
    """Resolve one canonical relative file without following a reparse component."""

    if not isinstance(relative_path, str) or not relative_path:
        raise IntegrityError(f"{label} path is invalid")
    relative = Path(relative_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or relative == Path(".")
        or ".." in relative.parts
        or relative.as_posix() != relative_path
    ):
        raise IntegrityError(f"{label} path is not canonical and relative")
    resolved_root = root.resolve(strict=True)
    current = resolved_root
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise IntegrityError(f"{label} is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse:
            raise IntegrityError(f"{label} path has a reparse component")
    if not stat.S_ISREG(metadata.st_mode):
        raise IntegrityError(f"{label} is not a regular file")
    try:
        current.resolve(strict=True).relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise IntegrityError(f"{label} escapes its configured root") from exc
    return current


def _open_relative_no_follow(root: Path, relative: Path, path: Path) -> int:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    if os.open not in os.supports_dir_fd or not hasattr(os, "O_DIRECTORY"):
        return os.open(path, flags)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    try:
        descriptors.append(os.open(root, directory_flags))
        for part in relative.parts[:-1]:
            descriptors.append(os.open(part, directory_flags, dir_fd=descriptors[-1]))
        return os.open(relative.name, flags, dir_fd=descriptors[-1])
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _descriptor_final_path(descriptor: int) -> Path | None:
    if os.name != "nt":
        return None
    import ctypes
    import msvcrt

    handle = msvcrt.get_osfhandle(descriptor)
    size = 512
    while True:
        buffer = ctypes.create_unicode_buffer(size)
        length = ctypes.windll.kernel32.GetFinalPathNameByHandleW(handle, buffer, size, 0)
        if length == 0:
            raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW failed")
        if length < size:
            value = buffer.value
            if value.startswith("\\\\?\\UNC\\"):
                value = "\\\\" + value[8:]
            elif value.startswith("\\\\?\\"):
                value = value[4:]
            return Path(value)
        size = length + 1


def read_contained_regular_file(root: Path, relative_path: object, *, label: str) -> bytes:
    """Read a contained regular file through a path bound during the open."""

    path = contained_regular_file(root, relative_path, label=label)
    relative = Path(str(relative_path))
    resolved_root = root.resolve(strict=True)
    try:
        before = path.lstat()
        descriptor = _open_relative_no_follow(resolved_root, relative, path)
    except OSError as exc:
        raise IntegrityError(f"{label} is unavailable") from exc
    try:
        opened = os.fstat(descriptor)
        after = path.lstat()
        final_path = _descriptor_final_path(descriptor)
        identity_fields = ("st_dev", "st_ino")
        if (
            not stat.S_ISREG(opened.st_mode)
            or any(getattr(opened, field) != getattr(before, field) for field in identity_fields)
            or any(getattr(opened, field) != getattr(after, field) for field in identity_fields)
        ):
            raise IntegrityError(f"{label} changed during read")
        if final_path is not None:
            try:
                opened_relative = final_path.relative_to(resolved_root)
            except ValueError as exc:
                raise IntegrityError(f"{label} escapes its configured root") from exc
            if opened_relative != relative:
                raise IntegrityError(f"{label} changed during read")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read()
        # Re-run the complete parent/reparse containment check after the read so
        # a redirected parent cannot silently supply bytes outside the root.
        contained_regular_file(root, relative_path, label=label)
        return raw
    except OSError as exc:
        raise IntegrityError(f"{label} is unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


__all__ = ["contained_regular_file", "read_contained_regular_file"]
