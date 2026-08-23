from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import time
from typing import Any, Iterator

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.lock import (
    _ExactGenerationBusyError,
    _raise_primary_with_cleanup,
    DirectoryAnchor,
    DirectoryMutationGuard,
    open_registered_root_anchor,
)


class _OwnedGenerationCleanupError(ConflictError):
    """A proven generation could not be unlinked because another writer still holds it."""


_OBJECT_PUBLICATION_GUARD = ".object-publication.guard"


def _after_object_temp_fsync(_temporary_name: str) -> None:
    """Test seam after a complete anchored temporary and before publication."""


def _remove_owned_generation(
    anchor: DirectoryAnchor,
    name: str,
    expected: os.stat_result,
    data: bytes,
    label: str,
    guard: DirectoryMutationGuard,
    *,
    missing_ok: bool = False,
    recover_after_parent_change: bool = False,
) -> None:
    """Unlink one attempt-owned anchored generation after re-proving its bytes."""

    if recover_after_parent_change:
        try:
            anchor.remove_exact_generation_after_parent_change(name, expected, data, guard=guard)
            return
        except _ExactGenerationBusyError as exc:
            raise _OwnedGenerationCleanupError(f"object publication {label} cleanup is temporarily busy") from exc
        except FileNotFoundError:
            if missing_ok:
                return
            raise ConflictError(f"object publication {label} generation changed") from None
        except OSError as exc:
            raise _OwnedGenerationCleanupError(f"object publication {label} cleanup failed") from exc
    try:
        observed_data, observed = anchor.read_regular_file_with_identity(name)
    except FileNotFoundError:
        if missing_ok:
            return
        raise ConflictError(f"object publication {label} generation changed") from None
    if not os.path.samestat(observed, expected):
        raise ConflictError(f"object publication {label} generation changed")
    if observed_data != data:
        raise ConflictError(f"object publication {label} bytes changed")
    try:
        anchor.remove_exact_generation(name, expected, data, guard=guard)
    except _ExactGenerationBusyError as exc:
        raise _OwnedGenerationCleanupError(f"object publication {label} cleanup is temporarily busy") from exc
    except FileNotFoundError:
        if missing_ok:
            return
        raise ConflictError(f"object publication {label} generation changed") from None
    except OSError as exc:
        raise _OwnedGenerationCleanupError(f"object publication {label} cleanup failed") from exc


def _require_exact_generation(
    anchor: DirectoryAnchor,
    name: str,
    expected: os.stat_result,
    data: bytes,
    label: str,
    *,
    missing_ok: bool = False,
) -> bool:
    """Prove one anchored member still has its original generation and bytes."""

    try:
        observed_data, observed = anchor.read_regular_file_with_identity(name)
    except FileNotFoundError:
        if missing_ok:
            return False
        raise ConflictError(f"object publication {label} generation changed") from None
    if not os.path.samestat(observed, expected):
        raise ConflictError(f"object publication {label} generation changed")
    if observed_data != data:
        raise ConflictError(f"object publication {label} bytes changed")
    return True


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


def _canonical_existing_revision_exists(anchor: DirectoryAnchor, prefix: str, description: str) -> bool:
    """Return true only when one complete canonical revision is physically proven."""

    try:
        return _canonical_existing_revision(anchor, prefix, description) is not None
    except ConflictError:
        return False


def _release_owned_claim_after_exact_completion(
    anchor: DirectoryAnchor,
    claim: str,
    claim_generation: os.stat_result,
    data: bytes,
    prefix: str,
    target: str,
    description: str,
    guard: DirectoryMutationGuard,
) -> None:
    """Release a claim only while its exact final remains provable."""

    for attempt in range(64):
        cleanup_error: ConflictError | None = None
        try:
            _remove_owned_generation(anchor, claim, claim_generation, data, "claim", guard, missing_ok=True)
            return
        except _OwnedGenerationCleanupError as exc:
            cleanup_error = exc
        except ConflictError as exc:
            # A peer can hold the exact shared claim briefly on Windows.  Only
            # an unchanged claim and an already-proven immutable final make
            # that contention retryable.
            try:
                _require_exact_generation(anchor, claim, claim_generation, data, "claim")
            except ConflictError:
                raise exc
            cleanup_error = exc
        assert cleanup_error is not None
        if _existing_revision(anchor, prefix, target, data, description) is None:
            raise cleanup_error
        if attempt == 63:
            raise cleanup_error
        time.sleep(0.005)


def _drain_claim_temporary_aliases(
    anchor: DirectoryAnchor,
    target: str,
    final_generation: os.stat_result,
    data: bytes,
    guard: DirectoryMutationGuard,
) -> None:
    """Remove only exact crashed temporary aliases after the immutable final is proven."""

    temporary_prefix = f".{target}."
    for name in anchor.list_names():
        if not name.startswith(temporary_prefix) or not name.endswith(".tmp"):
            continue
        try:
            temporary_data, temporary_generation = anchor.read_regular_file_with_identity(name)
        except (ConflictError, FileNotFoundError):
            continue
        if os.path.samestat(temporary_generation, final_generation) and temporary_data == data:
            _remove_owned_generation(anchor, name, temporary_generation, data, "temporary", guard, missing_ok=True)


def _drain_completed_claim(
    anchor: DirectoryAnchor,
    claim: str,
    data: bytes,
    prefix: str,
    target: str,
    description: str,
    guard: DirectoryMutationGuard,
) -> None:
    """Release only a claim and temporaries hard-linked to an exact completed final."""

    try:
        claim_data, claim_generation = anchor.read_regular_file_with_identity(claim)
    except (ConflictError, FileNotFoundError):
        return
    if claim_data != data:
        return
    final_data, final_generation = anchor.read_regular_file_with_identity(target)
    if final_data != data or not os.path.samestat(claim_generation, final_generation):
        return
    _drain_claim_temporary_aliases(anchor, target, final_generation, data, guard)
    _release_owned_claim_after_exact_completion(
        anchor, claim, claim_generation, data, prefix, target, description, guard
    )


def _write_object_in_directory(
    anchor: DirectoryAnchor,
    kind: str,
    object_id: str,
    revision: int,
    value: Any,
    guard: DirectoryMutationGuard,
) -> str:
    """Persist one immutable revision entirely through an opened directory anchor."""

    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError("object revision must be positive")
    data = canonical_bytes(value)
    digest = sha256_hex(data)
    prefix = f"{revision:08d}-"
    description = f"{kind}/{object_id}/{revision}"
    target = f"{prefix}{digest}.json"
    claim = f".{revision:08d}.publication-claim"
    existing = _existing_revision(anchor, prefix, target, data, description)
    if existing is not None:
        _drain_completed_claim(anchor, claim, data, prefix, target, description, guard)
        anchor.verify_unchanged()
        return existing

    temporary: str | None = None
    temporary_generation: os.stat_result | None = None
    claim_generation: os.stat_result | None = None
    claim_cleanup_anchor: str | None = None
    claim_cleanup_anchor_generation: os.stat_result | None = None
    final_generation: os.stat_result | None = None
    owns_claim = False
    owns_final = False
    claim_is_durable_recovery_state = False
    primary_error: BaseException | None = None
    try:
        temporary, temporary_generation = anchor.stage_private_file(target, data)
        anchor.fsync()
        _require_exact_generation(anchor, temporary, temporary_generation, data, "temporary")
        _after_object_temp_fsync(temporary)
        _require_exact_generation(anchor, temporary, temporary_generation, data, "temporary")
        existing = _existing_revision(anchor, prefix, target, data, description)
        if existing is not None:
            anchor.verify_unchanged()
            return existing
        try:
            claim_data, claim_generation = anchor.read_regular_file_with_identity(claim)
        except FileNotFoundError:
            try:
                claim_generation = anchor.link_exact_regular_file(temporary, temporary_generation, claim, guard=guard)
            except FileExistsError:
                try:
                    claim_data, claim_generation = anchor.read_regular_file_with_identity(claim)
                    if claim_data != data:
                        raise ConflictError("object publication claim bytes changed")
                    claim_cleanup_anchor = f".{claim}.{secrets.token_hex(16)}.cleanup-anchor"
                    claim_cleanup_anchor_generation = anchor.link_exact_regular_file(
                        claim,
                        claim_generation,
                        claim_cleanup_anchor,
                        guard=guard,
                    )
                    _require_exact_generation(anchor, claim, claim_generation, data, "claim")
                    _require_exact_generation(
                        anchor,
                        claim_cleanup_anchor,
                        claim_cleanup_anchor_generation,
                        data,
                        "claim cleanup anchor",
                    )
                    if not os.path.samestat(claim_generation, claim_cleanup_anchor_generation):
                        raise ConflictError("object publication claim generation changed")
                    anchor.fsync()
                except (ConflictError, FileNotFoundError):
                    # The owner may complete and remove its claim between this
                    # writer's no-replace link and inspection.  Only the exact
                    # immutable final makes that race idempotent.
                    existing = _existing_revision(anchor, prefix, target, data, description)
                    if existing is not None:
                        return existing
                    raise
            except ConflictError as exc:
                raise ConflictError("object publication claim generation changed") from exc
            else:
                owns_claim = True
                _require_exact_generation(anchor, temporary, temporary_generation, data, "temporary")
                _require_exact_generation(anchor, claim, claim_generation, data, "claim")
                if not os.path.samestat(temporary_generation, claim_generation):
                    raise ConflictError("object publication claim generation changed")
                anchor.fsync()
                claim_is_durable_recovery_state = True
        else:
            _require_exact_generation(anchor, claim, claim_generation, data, "claim")
        if claim_generation is None:
            raise ConflictError("object publication claim generation is unavailable")
        existing = _existing_revision(anchor, prefix, target, data, description)
        if existing is None:
            try:
                final_generation = anchor.link_exact_regular_file(claim, claim_generation, target, guard=guard)
            except FileExistsError:
                pass
            except ConflictError as exc:
                raise ConflictError("object publication final generation changed") from exc
            else:
                owns_final = True
                _require_exact_generation(anchor, claim, claim_generation, data, "claim")
                _require_exact_generation(anchor, target, final_generation, data, "final")
                if not os.path.samestat(claim_generation, final_generation):
                    raise ConflictError("object publication final generation changed")
                anchor.fsync()
        existing = _existing_revision(anchor, prefix, target, data, description)
        if existing is None:
            raise ConflictError("object publication final generation is unavailable")
        anchor.verify_unchanged()
        return existing
    except BaseException as exc:
        primary_error = exc
    finally:
        cleanup_error: BaseException | None = None
        if primary_error is not None and owns_final and final_generation is not None:
            # A recursive anchor fence can fail after the final link.  Roll
            # back only the generation created by this attempt through the held
            # leaf anchor; a substituted final remains untouched.
            try:
                _remove_owned_generation(
                    anchor,
                    target,
                    final_generation,
                    data,
                    "final",
                    guard,
                    missing_ok=True,
                    recover_after_parent_change=True,
                )
            except BaseException as exc:
                cleanup_error = exc
        if (
            primary_error is None
            and claim_cleanup_anchor is not None
            and claim_cleanup_anchor_generation is not None
            and claim_generation is not None
        ):
            try:
                _require_exact_generation(
                    anchor,
                    claim_cleanup_anchor,
                    claim_cleanup_anchor_generation,
                    data,
                    "claim cleanup anchor",
                )
                _require_exact_generation(anchor, claim, claim_generation, data, "claim")
                if not os.path.samestat(claim_generation, claim_cleanup_anchor_generation):
                    raise ConflictError("object publication claim generation changed")
                completed = _existing_revision(anchor, prefix, target, data, description)
                if completed is not None:
                    _drain_completed_claim(anchor, claim, data, prefix, target, description, guard)
            except BaseException as exc:
                if _existing_revision(anchor, prefix, target, data, description) is None:
                    cleanup_error = exc
        if claim_cleanup_anchor is not None and claim_cleanup_anchor_generation is not None:
            try:
                _remove_owned_generation(
                    anchor,
                    claim_cleanup_anchor,
                    claim_cleanup_anchor_generation,
                    data,
                    "claim cleanup anchor",
                    guard,
                    missing_ok=True,
                )
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
        if primary_error is None and claim_generation is not None and not owns_claim and claim_cleanup_anchor is None:
            try:
                completed = _existing_revision(anchor, prefix, target, data, description)
                if completed is not None:
                    _drain_completed_claim(anchor, claim, data, prefix, target, description, guard)
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
        preserve_claim_for_recovery = (
            primary_error is not None
            and owns_claim
            and claim_is_durable_recovery_state
            and not _canonical_existing_revision_exists(anchor, prefix, description)
        )
        if claim_generation is not None and owns_claim and not preserve_claim_for_recovery:
            try:
                if _existing_revision(anchor, prefix, target, data, description) is not None:
                    _drain_completed_claim(anchor, claim, data, prefix, target, description, guard)
                else:
                    _release_owned_claim_after_exact_completion(
                        anchor,
                        claim,
                        claim_generation,
                        data,
                        prefix,
                        target,
                        description,
                        guard,
                    )
            except BaseException as exc:
                cleanup_error = exc
        if temporary is not None and temporary_generation is not None:
            try:
                _remove_owned_generation(
                    anchor, temporary, temporary_generation, data, "temporary", guard, missing_ok=True
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
    """Persist an immutable content-addressed object revision under physical anchors."""

    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError("object revision must be positive")
    logical_directory = control_root / "objects" / kind / object_id
    with _anchored_object_directory(control_root, kind, object_id, create=True) as anchor:
        with anchor.acquire_mutation_guard(_OBJECT_PUBLICATION_GUARD) as guard:
            published = _write_object_in_directory(anchor, kind, object_id, revision, value, guard)
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
        try:
            with _anchored_object_directory(self.control_root, kind, object_id, create=False) as anchor:
                with anchor.acquire_mutation_guard(_OBJECT_PUBLICATION_GUARD) as guard:
                    matches = _revision_names(anchor, f"{revision:08d}-")
                    if not matches:
                        anchor.verify_unchanged()
                        return
                    expected_name = f"{revision:08d}-{sha256_hex(data)}.json"
                    if matches != (expected_name,):
                        raise IntegrityError("cannot roll back an ambiguous object revision")
                    observed_data, expected_generation = anchor.read_regular_file_with_identity(expected_name)
                    if observed_data != data:
                        raise IntegrityError("cannot roll back a changed object revision")
                    _remove_owned_generation(anchor, expected_name, expected_generation, data, "rollback final", guard)
                    anchor.verify_unchanged()
        except FileNotFoundError:
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
