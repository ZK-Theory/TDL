from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import time
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.ids import validate_id


def _after_object_temp_fsync(_temporary: Path) -> None:
    """Test seam after a complete durable temporary and before publication."""


def _existing_revision(
    directory: Path,
    prefix: str,
    data: bytes,
    description: str,
) -> Path | None:
    existing = sorted(directory.glob(f"{prefix}*.json"))
    if not existing:
        return None
    if len(existing) == 1 and existing[0].read_bytes() == data:
        return existing[0]
    raise ConflictError(f"object revision already exists: {description}")


def write_object(
    control_root: Path,
    kind: str,
    object_id: str,
    revision: int,
    value: Any,
) -> Path:
    """Persist one immutable object revision with content-addressed naming.

    Args:
        control_root: Canonical control-store root.
        kind: Registered object identity kind.
        object_id: Prefix-qualified object identity.
        revision: Positive immutable revision number.
        value: Canonical-JSON-compatible object content.

    Returns:
        Path to the existing or newly persisted matching revision.

    Raises:
        ConflictError: If the revision exists with different content.
        ValueError: If the identity or revision is invalid.
    """
    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError("object revision must be positive")
    data = canonical_bytes(value)
    digest = sha256_hex(data)
    directory = control_root / "objects" / kind / object_id
    directory.mkdir(parents=True, exist_ok=True)
    prefix = f"{revision:08d}-"
    description = f"{kind}/{object_id}/{revision}"
    existing = _existing_revision(directory, prefix, data, description)
    if existing is not None:
        return existing
    target = directory / f"{prefix}{digest}.json"
    temporary = directory / f".{target.name}.{secrets.token_hex(8)}.tmp"
    claim = directory / f".{revision:08d}.publication-claim"
    claim_descriptor = -1
    try:
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _after_object_temp_fsync(temporary)
        deadline = time.monotonic() + 30.0
        while claim_descriptor < 0:
            existing = _existing_revision(directory, prefix, data, description)
            if existing is not None:
                return existing
            try:
                claim_descriptor = os.open(
                    claim,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise ConflictError(f"object revision publication is busy: {description}") from None
                time.sleep(0.01)
        os.close(claim_descriptor)
        claim_descriptor = -2
        existing = _existing_revision(directory, prefix, data, description)
        if existing is not None:
            return existing
        os.link(temporary, target)
    finally:
        if claim_descriptor >= 0:
            os.close(claim_descriptor)
        if claim_descriptor == -2:
            claim.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
    return target


class ObjectStore:
    def __init__(self, control_root: Path):
        self.control_root = control_root

    def write(
        self,
        kind: str,
        object_id: str,
        revision: int,
        value: Any,
    ) -> Path:
        """Persist an immutable revision, idempotently on matching content.

        Args:
            kind: Registered object identity kind.
            object_id: Prefix-qualified object identity.
            revision: Positive immutable revision number.
            value: Canonical-JSON-compatible object content.

        Returns:
            Path to the existing or newly persisted matching revision.

        Raises:
            ConflictError: If the revision exists with different content.
            ValueError: If the identity or revision is invalid.
        """
        return write_object(self.control_root, kind, object_id, revision, value)

    def read(self, kind: str, object_id: str, revision: int) -> Any:
        """Resolve and verify one exact immutable object revision.

        Args:
            kind: Registered object identity kind.
            object_id: Prefix-qualified object identity.
            revision: Positive immutable revision number.

        Returns:
            Parsed canonical JSON content.

        Raises:
            IntegrityError: If the revision is missing, ambiguous, or tampered.
            ValueError: If the identity or revision is invalid.
        """
        validate_id(object_id, kind)
        if revision < 1:
            raise ValueError("object revision must be positive")
        directory = self.control_root / "objects" / kind / object_id
        try:
            matches = sorted(directory.glob(f"{revision:08d}-*.json"))
        except OSError as exc:
            raise IntegrityError("object revision is unreadable") from exc
        if len(matches) != 1:
            raise IntegrityError(f"object revision must resolve exactly once: {kind}/{object_id}/{revision}")
        path = matches[0]
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IntegrityError("object revision is unreadable") from exc
        try:
            value = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("object revision is not canonical JSON") from exc
        try:
            canonical = canonical_bytes(value)
        except (TypeError, ValueError) as exc:
            raise IntegrityError("object revision is not canonical JSON") from exc
        if canonical != data:
            raise IntegrityError("object revision bytes are not canonical")
        expected_name = f"{revision:08d}-{sha256_hex(data)}.json"
        if path.name != expected_name:
            raise IntegrityError("object revision filename hash mismatch")
        return value
