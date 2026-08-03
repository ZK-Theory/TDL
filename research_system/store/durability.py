"""Shared durability primitives for store directory-entry publication."""

from __future__ import annotations

import errno
import os
from pathlib import Path


def fsync_directory(path: Path) -> None:
    """Durably publish directory-entry changes where the platform permits.

    Platform denials that prevent opening or flushing a directory are tolerated;
    unexpected operating-system failures remain visible to the caller.
    """
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) == 5:
            return
        if exc.errno in {errno.EACCES, errno.EINVAL, errno.ENOTSUP}:
            return
        raise
    try:
        os.fsync(descriptor)
    except OSError as exc:
        if os.name != "nt" or getattr(exc, "winerror", None) not in {1, 5, 87}:
            raise
    finally:
        os.close(descriptor)
