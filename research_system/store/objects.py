from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import stat
import time
from typing import Any, Iterator

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.durability import fsync_directory
from research_system.store.lock import _ExactGenerationBusyError, DirectoryAnchor, open_registered_root_anchor


class _OwnedGenerationCleanupError(ConflictError):
    """A proven generation could not be unlinked because another writer still holds it."""


def _after_object_temp_fsync(_temporary: Path) -> None:
    """Test seam after a complete durable temporary and before publication."""


def _link_without_following(source: Path, destination: Path) -> None:
    """Create a hard link without silently following a substituted source path."""

    os.link(source, destination, follow_symlinks=False)


def _physical_generation(path: Path, label: str) -> os.stat_result:
    """Return the no-follow regular-file generation at one publication path."""

    try:
        observed = path.lstat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ConflictError(f"object publication {label} generation is unavailable") from exc
    attributes = getattr(observed, "st_file_attributes", 0)
    if stat.S_ISLNK(observed.st_mode) or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise ConflictError(f"object publication {label} is not a physical regular file")
    if not stat.S_ISREG(observed.st_mode):
        raise ConflictError(f"object publication {label} is not a regular file")
    return observed


def _require_generation(
    path: Path,
    expected: os.stat_result,
    label: str,
    *,
    missing_ok: bool = False,
) -> bool:
    """Reject a path whose filesystem generation differs from the held one."""

    try:
        observed = _physical_generation(path, label)
    except FileNotFoundError:
        if missing_ok:
            return False
        raise ConflictError(f"object publication {label} generation changed") from None
    if not os.path.samestat(observed, expected):
        raise ConflictError(f"object publication {label} generation changed")
    return True


def _read_exact_generation(
    path: Path,
    expected: os.stat_result,
    data: bytes,
    label: str,
    *,
    missing_ok: bool = False,
) -> bool:
    """Prove the held generation still carries the exact publication bytes."""

    try:
        if missing_ok:
            observed_data = _read_physical_generation(path, expected, label, missing_ok=True)
        else:
            # Preserve the long-standing private test seam's three-argument
            # call shape for ordinary exact reads.
            observed_data = _read_physical_generation(path, expected, label)
    except FileNotFoundError:
        if missing_ok:
            return False
        raise ConflictError(f"object publication {label} generation changed") from None
    if observed_data is None:
        return False
    if not _require_generation(path, expected, label, missing_ok=missing_ok):
        return False
    if observed_data != data:
        raise ConflictError(f"object publication {label} bytes changed")
    return True


def _read_physical_generation(
    path: Path,
    expected: os.stat_result,
    label: str,
    *,
    missing_ok: bool = False,
) -> bytes | None:
    """Read one already-proven physical regular-file generation without following it."""

    if not _require_generation(path, expected, label, missing_ok=missing_ok):
        return None
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(opened, expected):
                raise ConflictError(f"object publication {label} generation changed")
            observed_data = handle.read()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ConflictError(f"object publication {label} bytes are unreadable") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if not _require_generation(path, expected, label, missing_ok=missing_ok):
        return None
    return observed_data


def _remove_owned_generation(
    path: Path,
    expected: os.stat_result,
    data: bytes,
    directory: Path,
    anchor: DirectoryAnchor,
    label: str,
    *,
    missing_ok: bool = False,
) -> None:
    """Unlink one attempt-owned path only after re-proving its generation."""

    try:
        if not _read_exact_generation(path, expected, data, label, missing_ok=missing_ok):
            return
    except ConflictError:
        raise
    except FileNotFoundError:
        if missing_ok:
            return
        raise ConflictError(f"object publication {label} generation changed") from None
    try:
        anchor.remove_exact_generation(path.name, expected, data)
    except FileNotFoundError:
        if missing_ok:
            return
        raise ConflictError(f"object publication {label} generation changed") from None
    except _ExactGenerationBusyError as exc:
        raise _OwnedGenerationCleanupError(f"object publication {label} cleanup is temporarily busy") from exc
    except OSError as exc:
        raise _OwnedGenerationCleanupError(f"object publication {label} cleanup failed") from exc
    fsync_directory(directory)


@contextmanager
def _anchored_object_directory(
    control_root: Path,
    kind: str,
    object_id: str,
    *,
    create: bool,
) -> Iterator[tuple[DirectoryAnchor, Path]]:
    """Hold physical anchors for ``objects/<kind>/<object_id>`` throughout an operation."""

    if create:
        control_root.mkdir(parents=True, exist_ok=True)
    root_anchor: DirectoryAnchor | None = None
    objects_anchor: DirectoryAnchor | None = None
    kind_anchor: DirectoryAnchor | None = None
    object_anchor: DirectoryAnchor | None = None
    try:
        root_anchor = open_registered_root_anchor(control_root, delete_protect=False)
        objects_anchor = root_anchor.open_member_directory("objects", create=create, delete_protect=False)
        kind_anchor = objects_anchor.open_member_directory(kind, create=create, delete_protect=False)
        object_anchor = kind_anchor.open_member_directory(object_id, create=create, delete_protect=False)
        yield object_anchor, object_anchor.final_path
    finally:
        first_error: BaseException | None = None
        for anchor in (object_anchor, kind_anchor, objects_anchor, root_anchor):
            if anchor is None:
                continue
            try:
                anchor.close()
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error


def _existing_revision(
    directory: Path,
    anchor: DirectoryAnchor,
    prefix: str,
    target: Path,
    data: bytes,
    description: str,
) -> Path | None:
    existing = _canonical_existing_revision(directory, anchor, prefix, description)
    if existing is None:
        return None
    path, stored_data = existing
    if path.name == target.name and stored_data == data:
        return path
    raise ConflictError(f"object revision already exists: {description}")


def _canonical_existing_revision(
    directory: Path,
    anchor: DirectoryAnchor,
    prefix: str,
    description: str,
) -> tuple[Path, bytes] | None:
    existing = _revision_names(anchor, prefix)
    if not existing:
        return None
    if len(existing) != 1:
        raise ConflictError(f"object revision already exists: {description}")
    path = directory / existing[0]
    try:
        generation = _physical_generation(path, "existing final")
        data = _read_physical_generation(path, generation, "existing final")
    except (ConflictError, FileNotFoundError) as exc:
        raise ConflictError(f"object revision already exists: {description}") from exc
    try:
        value = json.loads(data)
        canonical = canonical_bytes(value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ConflictError(f"object revision already exists: {description}") from exc
    expected_name = f"{prefix}{sha256_hex(data)}.json"
    if canonical != data or path.name != expected_name:
        raise ConflictError(f"object revision already exists: {description}")
    return path, data


def _revision_names(anchor: DirectoryAnchor, prefix: str) -> tuple[str, ...]:
    """Return immediate canonical-candidate names from one physical object directory."""

    return tuple(sorted(name for name in anchor.list_names() if name.startswith(prefix) and name.endswith(".json")))


def _canonical_existing_revision_exists(
    directory: Path,
    anchor: DirectoryAnchor,
    prefix: str,
    description: str,
) -> bool:
    """Return true only when one complete canonical revision is physically proven."""

    try:
        return _canonical_existing_revision(directory, anchor, prefix, description) is not None
    except ConflictError:
        return False


def _release_owned_claim_after_exact_completion(
    claim: Path,
    claim_generation: os.stat_result,
    data: bytes,
    directory: Path,
    prefix: str,
    target: Path,
    anchor: DirectoryAnchor,
    description: str,
) -> None:
    """Release the winning writer's claim after the exact final is durable.

    A concurrent identical writer may briefly be reading the shared claim on
    Windows.  That is the only retryable cleanup case: the claim's generation
    remains proven and the immutable final already matches exactly.  Any other
    claim disturbance is a conflict and is never treated as normal contention.
    """

    for attempt in range(64):
        cleanup_error: ConflictError | None = None
        try:
            _remove_owned_generation(claim, claim_generation, data, directory, anchor, "claim", missing_ok=True)
            return
        except _OwnedGenerationCleanupError as exc:
            cleanup_error = exc
        except ConflictError as exc:
            # Windows can report a peer's still-open exact claim as an access
            # error rather than the sharing-violation code.  Recheck both
            # immutable facts before considering it retryable; a substituted
            # claim or final remains the original conflict and is never retried.
            try:
                _read_exact_generation(claim, claim_generation, data, "claim")
            except ConflictError:
                raise exc
            cleanup_error = exc
        assert cleanup_error is not None
        if _existing_revision(directory, anchor, prefix, target, data, description) is None:
            raise cleanup_error
        if attempt == 63:
            raise cleanup_error
        time.sleep(0.005)


def _claim_has_live_private_producer(
    directory: Path,
    anchor: DirectoryAnchor,
    target: Path,
    claim_generation: os.stat_result,
) -> bool:
    """Return whether a still-live staged generation proves another writer owns the claim."""

    temporary_prefix = f".{target.name}."
    for name in anchor.list_names():
        if not name.startswith(temporary_prefix) or not name.endswith(".tmp"):
            continue
        try:
            temporary_generation = _physical_generation(directory / name, "concurrent temporary")
        except (ConflictError, FileNotFoundError):
            continue
        if os.path.samestat(temporary_generation, claim_generation):
            return True
    return False


def _write_object_in_directory(
    directory: Path,
    anchor: DirectoryAnchor,
    kind: str,
    object_id: str,
    revision: int,
    value: Any,
) -> Path:
    """Persist one object revision below an already-held physical directory anchor."""
    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError("object revision must be positive")
    data = canonical_bytes(value)
    digest = sha256_hex(data)
    prefix = f"{revision:08d}-"
    description = f"{kind}/{object_id}/{revision}"
    target = directory / f"{prefix}{digest}.json"
    existing = _existing_revision(directory, anchor, prefix, target, data, description)
    if existing is not None:
        return existing
    temporary = directory / f".{target.name}.{secrets.token_hex(8)}.tmp"
    claim = directory / f".{revision:08d}.publication-claim"
    temporary_generation: os.stat_result | None = None
    claim_generation: os.stat_result | None = None
    claim_cleanup_anchor: Path | None = None
    claim_cleanup_anchor_generation: os.stat_result | None = None
    owns_claim = False
    claim_is_durable_recovery_state = False
    primary_error: BaseException | None = None
    try:
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_generation = os.fstat(handle.fileno())
        if not stat.S_ISREG(temporary_generation.st_mode):
            raise ConflictError("object publication temporary is not a regular file")
        _read_exact_generation(temporary, temporary_generation, data, "temporary")
        fsync_directory(directory)
        _after_object_temp_fsync(temporary)
        _read_exact_generation(temporary, temporary_generation, data, "temporary")
        existing = _existing_revision(directory, anchor, prefix, target, data, description)
        if existing is not None:
            return existing
        try:
            _link_without_following(temporary, claim)
        except FileExistsError:
            try:
                claim_generation = _physical_generation(claim, "claim")
                _read_exact_generation(claim, claim_generation, data, "claim")
                claim_cleanup_anchor = claim.with_name(f".{claim.name}.{secrets.token_hex(8)}.cleanup-anchor")
                _link_without_following(claim, claim_cleanup_anchor)
                claim_cleanup_anchor_generation = _physical_generation(
                    claim_cleanup_anchor,
                    "claim cleanup anchor",
                )
                _read_exact_generation(claim, claim_generation, data, "claim")
                _read_exact_generation(
                    claim_cleanup_anchor,
                    claim_cleanup_anchor_generation,
                    data,
                    "claim cleanup anchor",
                )
                if not os.path.samestat(claim_generation, claim_cleanup_anchor_generation):
                    raise ConflictError("object publication claim generation changed")
                fsync_directory(directory)
            except (ConflictError, FileNotFoundError):
                # The winning writer may have sealed the final object and
                # removed its claim between our exclusive-link attempt and
                # inspection.  Only that exact completed revision is a safe
                # idempotent result; every other claim disturbance remains a
                # conflict.
                existing = _existing_revision(directory, anchor, prefix, target, data, description)
                if existing is not None:
                    return existing
                raise
        else:
            owns_claim = True
            claim_generation = _physical_generation(claim, "claim")
            _read_exact_generation(temporary, temporary_generation, data, "temporary")
            _read_exact_generation(claim, claim_generation, data, "claim")
            if not os.path.samestat(temporary_generation, claim_generation):
                raise ConflictError("object publication claim generation changed")
            fsync_directory(directory)
            claim_is_durable_recovery_state = True
        if claim_generation is None:
            raise ConflictError("object publication claim generation is unavailable")
        existing = _existing_revision(directory, anchor, prefix, target, data, description)
        if existing is None:
            try:
                _link_without_following(claim, target)
            except FileExistsError:
                pass
            else:
                _read_exact_generation(claim, claim_generation, data, "claim")
                final_generation = _physical_generation(target, "final")
                _read_exact_generation(target, final_generation, data, "final")
                if not os.path.samestat(claim_generation, final_generation):
                    raise ConflictError("object publication final generation changed")
                fsync_directory(directory)
        existing = _existing_revision(directory, anchor, prefix, target, data, description)
        if existing is None:
            raise ConflictError("object publication final generation is unavailable")
        return existing
    except BaseException as exc:
        primary_error = exc
    finally:
        cleanup_error: BaseException | None = None
        if (
            primary_error is None
            and claim_cleanup_anchor is not None
            and claim_cleanup_anchor_generation is not None
            and claim_generation is not None
        ):
            try:
                _read_exact_generation(
                    claim_cleanup_anchor,
                    claim_cleanup_anchor_generation,
                    data,
                    "claim cleanup anchor",
                )
                _read_exact_generation(claim, claim_generation, data, "claim")
                if not os.path.samestat(claim_generation, claim_cleanup_anchor_generation):
                    raise ConflictError("object publication claim generation changed")
                completed = _existing_revision(directory, anchor, prefix, target, data, description)
                if completed is not None and not _claim_has_live_private_producer(
                    directory,
                    anchor,
                    target,
                    claim_generation,
                ):
                    _release_owned_claim_after_exact_completion(
                        claim,
                        claim_generation,
                        data,
                        directory,
                        prefix,
                        target,
                        anchor,
                        description,
                    )
            except BaseException as exc:
                # A concurrent owner can remove the exact shared claim after
                # sealing the same final object.  A non-owner only proves the
                # shared claim and then releases its own cleanup anchor; the
                # claim owner alone performs the shared unlink.
                if _existing_revision(directory, anchor, prefix, target, data, description) is None:
                    cleanup_error = exc
        if claim_cleanup_anchor is not None and claim_cleanup_anchor_generation is not None:
            try:
                _remove_owned_generation(
                    claim_cleanup_anchor,
                    claim_cleanup_anchor_generation,
                    data,
                    directory,
                    anchor,
                    "claim cleanup anchor",
                    missing_ok=True,
                )
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
        preserve_claim_for_recovery = (
            primary_error is not None
            and owns_claim
            and claim_is_durable_recovery_state
            and not _canonical_existing_revision_exists(directory, anchor, prefix, description)
        )
        if owns_claim and claim_generation is not None and not preserve_claim_for_recovery:
            try:
                _release_owned_claim_after_exact_completion(
                    claim,
                    claim_generation,
                    data,
                    directory,
                    prefix,
                    target,
                    anchor,
                    description,
                )
            except BaseException as exc:
                cleanup_error = exc
        if temporary_generation is not None:
            try:
                _remove_owned_generation(
                    temporary,
                    temporary_generation,
                    data,
                    directory,
                    anchor,
                    "temporary",
                    missing_ok=True,
                )
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
        if primary_error is not None:
            if cleanup_error is not None:
                raise primary_error from cleanup_error
            raise primary_error
        if cleanup_error is not None:
            raise cleanup_error


def write_object(
    control_root: Path,
    kind: str,
    object_id: str,
    revision: int,
    value: Any,
) -> Path:
    """Persist one immutable content-addressed object revision under physical anchors."""

    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError("object revision must be positive")
    logical_directory = control_root / "objects" / kind / object_id
    with _anchored_object_directory(control_root, kind, object_id, create=True) as (anchor, directory):
        published = _write_object_in_directory(directory, anchor, kind, object_id, revision, value)
    return logical_directory / published.name


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
        logical_directory = self.control_root / "objects" / kind / object_id
        if not logical_directory.exists():
            return False
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as (anchor, _directory):
                return bool(_revision_names(anchor, f"{revision:08d}-"))
        except (ConflictError, OSError) as exc:
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
        logical_directory = self.control_root / "objects" / kind / object_id
        if not logical_directory.exists():
            return
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as (anchor, directory):
                matches = _revision_names(anchor, f"{revision:08d}-")
                if not matches:
                    return
                expected_name = f"{revision:08d}-{sha256_hex(data)}.json"
                if matches != (expected_name,):
                    raise IntegrityError("cannot roll back an ambiguous object revision")
                expected = directory / expected_name
                expected_generation = _physical_generation(expected, "rollback final")
                _remove_owned_generation(
                    expected,
                    expected_generation,
                    data,
                    directory,
                    anchor,
                    "rollback final",
                )
        except ConflictError as exc:
            raise IntegrityError("cannot roll back a changed object revision") from exc
        except OSError as exc:
            raise IntegrityError("object revision is unreadable") from exc
        except FileNotFoundError as exc:
            raise IntegrityError("cannot roll back a changed object revision") from exc

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
        logical_directory = self.control_root / "objects" / kind / object_id
        if not logical_directory.exists():
            return None
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as (anchor, _directory):
                names = tuple(name for name in anchor.list_names() if name.endswith(".json"))
        except (ConflictError, OSError) as exc:
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
        logical_directory = self.control_root / "objects" / kind / object_id
        if not logical_directory.exists():
            raise IntegrityError(f"object revision must resolve exactly once: {kind}/{object_id}/{revision}")
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as (anchor, directory):
                names = _revision_names(anchor, f"{revision:08d}-")
                if len(names) != 1:
                    raise IntegrityError(f"object revision must resolve exactly once: {kind}/{object_id}/{revision}")
                path = directory / names[0]
                generation = _physical_generation(path, "read final")
                data = _read_physical_generation(path, generation, "read final")
        except (ConflictError, OSError) as exc:
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
