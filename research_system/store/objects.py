from __future__ import annotations

import errno
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


def _fsync_directory(path: Path) -> None:
    """Durably publish directory-entry changes where the platform permits."""
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


def _existing_revision(
    directory: Path,
    prefix: str,
    target: Path,
    data: bytes,
    description: str,
) -> Path | None:
    existing = _canonical_existing_revision(directory, prefix, description)
    if existing is None:
        return None
    path, stored_data = existing
    if path.name == target.name and stored_data == data:
        return path
    raise ConflictError(f"object revision already exists: {description}")


def _canonical_existing_revision(
    directory: Path,
    prefix: str,
    description: str,
) -> tuple[Path, bytes] | None:
    existing = sorted(directory.glob(f"{prefix}*.json"))
    if not existing:
        return None
    if len(existing) != 1:
        raise ConflictError(f"object revision already exists: {description}")
    path = existing[0]
    data = path.read_bytes()
    try:
        value = json.loads(data)
        canonical = canonical_bytes(value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ConflictError(f"object revision already exists: {description}") from exc
    expected_name = f"{prefix}{sha256_hex(data)}.json"
    if canonical != data or path.name != expected_name:
        raise ConflictError(f"object revision already exists: {description}")
    return path, data


def _remove_claim(claim: Path, directory: Path) -> None:
    for attempt in range(100):
        try:
            claim.unlink()
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt == 99:
                raise
            time.sleep(0.001)
        else:
            _fsync_directory(directory)
            return


def _claim_data(claim: Path) -> bytes | None:
    try:
        data = claim.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise IntegrityError("object revision publication claim is unreadable") from exc
    try:
        value = json.loads(data)
        canonical = canonical_bytes(value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise IntegrityError("object revision publication claim is not canonical JSON") from exc
    if canonical != data:
        raise IntegrityError("object revision publication claim bytes are not canonical")
    return data


def _complete_claim(
    directory: Path,
    prefix: str,
    claim: Path,
    description: str,
) -> Path | None:
    data = _claim_data(claim)
    if data is None:
        return None
    target = directory / f"{prefix}{sha256_hex(data)}.json"
    committed = _canonical_existing_revision(directory, prefix, description)
    if committed is None:
        try:
            os.link(claim, target)
        except (FileExistsError, FileNotFoundError):
            pass
        except PermissionError:
            if _canonical_existing_revision(directory, prefix, description) is None:
                raise
        else:
            _fsync_directory(directory)
        committed = _canonical_existing_revision(directory, prefix, description)
    if committed is not None:
        _remove_claim(claim, directory)
        return committed[0]
    return None


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
    target = directory / f"{prefix}{digest}.json"
    claim = directory / f".{revision:08d}.publication-claim"
    existing = _existing_revision(directory, prefix, target, data, description)
    if existing is not None:
        _remove_claim(claim, directory)
        return existing
    temporary = directory / f".{target.name}.{secrets.token_hex(8)}.tmp"
    try:
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _after_object_temp_fsync(temporary)
        while True:
            existing = _existing_revision(directory, prefix, target, data, description)
            if existing is not None:
                _remove_claim(claim, directory)
                return existing
            try:
                os.link(temporary, claim)
            except FileExistsError:
                pass
            else:
                _fsync_directory(directory)
            if _complete_claim(directory, prefix, claim, description) is None:
                continue
            existing = _existing_revision(directory, prefix, target, data, description)
            if existing is not None:
                return existing
    finally:
        temporary.unlink(missing_ok=True)


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

    def revision_exists(self, kind: str, object_id: str, revision: int) -> bool:
        """Return whether one immutable revision was present before a transaction.

        This is intentionally a presence check rather than a content read. A
        caller preparing a rollback must treat every pre-existing revision as
        owned by the store, including a malformed or conflicting one.
        """
        validate_id(object_id, kind)
        if revision < 1:
            raise ValueError("object revision must be positive")
        directory = self.control_root / "objects" / kind / object_id
        try:
            return any(directory.glob(f"{revision:08d}-*.json"))
        except OSError as exc:
            raise IntegrityError("object revision is unreadable") from exc

    def rollback_new_revision(
        self,
        kind: str,
        object_id: str,
        revision: int,
        value: Any,
        *,
        existed_before: bool,
    ) -> None:
        """Remove only an exact revision created by the current locked write.

        The caller must hold the store writer lock. A pre-existing revision is
        never touched. When the revision was absent at capture time, removal
        still requires exactly one canonical filename and byte-identical
        content, so a changed or ambiguous object is preserved and reported.
        """
        if existed_before:
            return
        validate_id(object_id, kind)
        if revision < 1:
            raise ValueError("object revision must be positive")
        data = canonical_bytes(value)
        directory = self.control_root / "objects" / kind / object_id
        try:
            matches = sorted(directory.glob(f"{revision:08d}-*.json"))
        except OSError as exc:
            raise IntegrityError("object revision is unreadable") from exc
        if not matches:
            return
        expected = directory / f"{revision:08d}-{sha256_hex(data)}.json"
        if matches != [expected]:
            raise IntegrityError("cannot roll back an ambiguous object revision")
        try:
            current = expected.read_bytes()
        except OSError as exc:
            raise IntegrityError("object revision is unreadable") from exc
        if current != data:
            raise IntegrityError("cannot roll back a changed object revision")
        try:
            expected.unlink()
        except OSError as exc:
            raise IntegrityError("object revision rollback failed") from exc
        _fsync_directory(directory)

    def latest_revision(self, kind: str, object_id: str) -> int | None:
        """Return the highest persisted revision for an object identity.

        Revisions are immutable and content-addressed, so a caller that resolves
        the latest revision twice observes a change only when a genuinely new
        revision was published in between. That is the signal a supersession
        check needs, so this deliberately does not cache.

        Args:
            kind: Registered object identity kind.
            object_id: Prefix-qualified object identity.

        Returns:
            The highest persisted revision, or ``None`` when the identity has none.

        Raises:
            IntegrityError: If the object directory is unreadable or malformed.
            ValueError: If the identity is invalid.
        """
        validate_id(object_id, kind)
        directory = self.control_root / "objects" / kind / object_id
        try:
            names = [path.name for path in directory.glob("*.json")]
        except OSError as exc:
            raise IntegrityError("object identity is unreadable") from exc
        revisions: list[int] = []
        for name in names:
            prefix = name.split("-", 1)[0]
            if len(prefix) != 8 or not prefix.isdigit():
                raise IntegrityError(f"object revision filename is malformed: {kind}/{object_id}/{name}")
            revisions.append(int(prefix))
        return max(revisions) if revisions else None

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
