from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Iterator

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.anchor import (
    DirectoryAnchor,
    DirectoryTransaction,
    _raise_primary_with_cleanup,
    open_registered_root_anchor,
)


def _after_object_temp_fsync(_temporary_name: str) -> None:
    """Test seam after a complete anchored temporary and before publication."""


@contextmanager
def _anchored_object_directory(
    control_root: Path,
    kind: str,
    object_id: str,
    *,
    create: bool,
) -> Iterator[DirectoryAnchor]:
    """Hold each physical ``objects/<kind>/<object_id>`` generation for one operation."""

    if create:
        control_root.mkdir(parents=True, exist_ok=True)
    root_anchor: DirectoryAnchor | None = None
    objects_anchor: DirectoryAnchor | None = None
    kind_anchor: DirectoryAnchor | None = None
    object_anchor: DirectoryAnchor | None = None
    primary_error: BaseException | None = None
    try:
        # Retained anchors remain compatible between identical writers.  Every
        # Windows lexical effect takes the leaf's short-lived exact-generation
        # fence; POSIX effects are relative to the retained directory handle.
        root_anchor = open_registered_root_anchor(control_root, delete_protect=False)
        objects_anchor = root_anchor.open_member_directory("objects", create=create, delete_protect=False)
        kind_anchor = objects_anchor.open_member_directory(kind, create=create, delete_protect=False)
        object_anchor = kind_anchor.open_member_directory(object_id, create=create, delete_protect=False)
        yield object_anchor
    except BaseException as exc:
        primary_error = exc
        raise
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
        if primary_error is not None and first_error is not None:
            _raise_primary_with_cleanup(primary_error, first_error)
        if first_error is not None:
            raise first_error


def _revision_names(anchor: DirectoryAnchor, prefix: str) -> tuple[str, ...]:
    """Return immediate canonical-candidate names from one physical object directory."""

    return tuple(sorted(name for name in anchor.list_names() if name.startswith(prefix) and name.endswith(".json")))


def _canonical_existing_revision(
    anchor: DirectoryAnchor,
    prefix: str,
    description: str,
) -> tuple[str, bytes] | None:
    """Read and validate the sole complete revision in the held directory."""

    existing = _revision_names(anchor, prefix)
    if not existing:
        return None
    if len(existing) != 1:
        raise ConflictError(f"object revision already exists: {description}")
    name = existing[0]
    try:
        data, _generation = anchor.read_regular_file_with_identity(name)
        value = json.loads(data)
        canonical = canonical_bytes(value)
    except (ConflictError, FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ConflictError(f"object revision already exists: {description}") from exc
    expected_name = f"{prefix}{sha256_hex(data)}.json"
    if canonical != data or name != expected_name:
        raise ConflictError(f"object revision already exists: {description}")
    return name, data


def _existing_revision(
    anchor: DirectoryAnchor,
    prefix: str,
    target_name: str,
    data: bytes,
    description: str,
) -> str | None:
    """Resolve an idempotent exact revision or reject a conflicting revision."""

    existing = _canonical_existing_revision(anchor, prefix, description)
    if existing is None:
        return None
    name, stored_data = existing
    if name == target_name and stored_data == data:
        return name
    raise ConflictError(f"object revision already exists: {description}")


def _write_object_in_directory(
    anchor: DirectoryAnchor,
    kind: str,
    object_id: str,
    revision: int,
    value: Any,
    transaction: DirectoryTransaction,
) -> str:
    """Publish one immutable revision through the canonical transaction.

    The old claim/rollback construction deliberately is not called here.  Once
    ``DirectoryTransaction.adopt_or_publish`` links the final name, the
    publication attempt has committed namespace state; later fallible work is
    resolved only by an identical retry.
    """

    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError("object revision must be positive")
    data = canonical_bytes(value)
    digest = sha256_hex(data)
    prefix = f"{revision:08d}-"
    description = f"{kind}/{object_id}/{revision}"
    target = f"{prefix}{digest}.json"

    existing = _existing_revision(anchor, prefix, target, data, description)
    if existing is not None:
        transaction.recover_private_stages(target, data)
        anchor.verify_unchanged()
        return existing

    stage = transaction.stage(target, data)
    _after_object_temp_fsync(stage.name)
    transaction.verify_stage(stage)
    # A same-UID bypass can create a foreign final despite the guard.  The
    # transaction observes it and fails closed unless it is the exact bytes
    # this retry was trying to publish.
    transaction.adopt_or_publish(stage, target)
    transaction.discard_stage(stage)
    transaction.recover_private_stages(target, data)
    anchor.verify_unchanged()
    return target


def write_object(
    control_root: Path,
    kind: str,
    object_id: str,
    revision: int,
    value: Any,
) -> Path:
    """Persist an immutable content-addressed object revision under physical anchors."""

    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError("object revision must be positive")
    logical_directory = control_root / "objects" / kind / object_id
    with _anchored_object_directory(control_root, kind, object_id, create=True) as anchor:
        with DirectoryTransaction(anchor) as transaction:
            published = _write_object_in_directory(anchor, kind, object_id, revision, value, transaction)
    return logical_directory / published


class ObjectStore:
    def __init__(self, control_root: Path):
        self.control_root = control_root

    def write(self, kind: str, object_id: str, revision: int, value: Any) -> Path:
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
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as anchor:
                present = bool(_revision_names(anchor, f"{revision:08d}-"))
                anchor.verify_unchanged()
                return present
        except FileNotFoundError:
            return False
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
        captured_generation = False
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as anchor:
                with DirectoryTransaction(anchor) as transaction:
                    matches = _revision_names(anchor, f"{revision:08d}-")
                    if not matches:
                        # A prior rollback may have unlinked this revision but
                        # failed before its directory flush.  Visibility alone
                        # is not durable rollback success: re-establish the
                        # anchored directory durability and then prove that no
                        # revision reappeared while doing so.
                        anchor.fsync()
                        if _revision_names(anchor, f"{revision:08d}-"):
                            raise IntegrityError("cannot roll back a changed object revision")
                        anchor.verify_unchanged()
                        return
                    expected_name = f"{revision:08d}-{sha256_hex(data)}.json"
                    if matches != (expected_name,):
                        raise IntegrityError("cannot roll back an ambiguous object revision")
                    observed_data, expected_generation = anchor.read_regular_file_with_identity(expected_name)
                    if observed_data != data:
                        raise IntegrityError("cannot roll back a changed object revision")
                    captured_generation = True
                    # This is an explicit higher-level recovery authority, not
                    # an implicit publication rollback.  It nevertheless uses
                    # the same transaction receipt and fixed guard as every
                    # other STORE namespace effect.
                    transaction.remove_exact_final(expected_name, expected_generation, data)
                    anchor.verify_unchanged()
        except FileNotFoundError as exc:
            if captured_generation:
                raise IntegrityError("cannot roll back a changed object revision") from exc
            return
        except ConflictError as exc:
            raise IntegrityError("cannot roll back a changed object revision") from exc
        except OSError as exc:
            raise IntegrityError("object revision is unreadable") from exc

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
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as anchor:
                names = tuple(name for name in anchor.list_names() if name.endswith(".json"))
                anchor.verify_unchanged()
        except FileNotFoundError:
            return None
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
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as anchor:
                names = _revision_names(anchor, f"{revision:08d}-")
                if len(names) != 1:
                    raise IntegrityError(f"object revision must resolve exactly once: {kind}/{object_id}/{revision}")
                name = names[0]
                data, _generation = anchor.read_regular_file_with_identity(name)
                anchor.verify_unchanged()
        except FileNotFoundError as exc:
            raise IntegrityError(f"object revision must resolve exactly once: {kind}/{object_id}/{revision}") from exc
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
        if name != expected_name:
            raise IntegrityError("object revision filename hash mismatch")
        return value
