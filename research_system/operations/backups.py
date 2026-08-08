"""W8 backup receipts and authority-bound restore preflight evidence."""

from __future__ import annotations

import ctypes
import errno
import json
import os
import stat
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.projection.replay import replay
from research_system.store.identity import (
    StoreOriginWitness,
    _fsync_directory,
    _require_physical_disjoint,
    _require_physical_path,
    _restore_preflight_anchor,
    canonical_restore_binding_output,
    load_store_manifest,
    load_store_manifest_unbound,
    manifest_schema_root,
    validate_approved_origin_witness_path,
)
from research_system.store.layout import require_existing_control_root
from research_system.store.ledger import EventLedger, LedgerSnapshot
from research_system.schema_registry import bundled_runtime_schema_registry


_WINDOWS_RESERVED_FILENAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"} | {f"COM{index}" for index in range(1, 10)} | {f"LPT{index}" for index in range(1, 10)}
)


@dataclass(frozen=True, slots=True)
class ArtefactBinding:
    artefact_id: str
    artefact_hash: str


@dataclass(frozen=True, slots=True)
class BackupReceipt:
    receipt_id: str
    receipt_revision: int
    receipt_hash: str
    project_id: str
    store_identity: str
    canonical_tail_position: int
    canonical_tail_hash: str
    snapshot_id: str
    snapshot_hash: str
    snapshot_source_position: int
    snapshot_source_hash: str
    snapshot_state_hash: str
    replay_start_position: int
    replay_end_position: int
    schema_versions: tuple[str, ...]
    tool_versions: tuple[str, ...]
    encryption_class: str
    redaction_class: str
    external_artefact_manifest_hash: str
    artefact_bindings: tuple[ArtefactBinding, ...]
    availability_status: str
    availability_observation_hash: str
    created_at: str
    created_by_actor_id: str
    verified_at: str
    verified_by_actor_id: str
    verification_authority_grant_id: str
    destination_class: str
    source_endpoint_scheme: str
    evidence_registry_hash: str


@dataclass(frozen=True, slots=True)
class BackupArtefactInput:
    """One owner-supplied external artefact observation for a backup."""

    artefact_id: str
    source_path: Path
    content_sha256: str
    availability: str
    availability_evidence_refs: tuple[str, ...]
    observed_at: str


@dataclass(frozen=True, slots=True)
class BackupPreparation:
    """Durable hidden backup candidate and its exact event payload."""

    command_id: str
    stage_root: Path
    destination_root: Path
    preparation_sha256: str
    event_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RestorePreflightResult:
    status: str
    failed_predicates: tuple[str, ...]
    receipt_hash: str
    ledger_hash: str
    snapshot_hash: str
    target_endpoint_ownership_hash: str
    artefact_manifest_hash: str
    availability_observations_hash: str
    registry_hash: str
    target_root: str
    project_id: str
    store_identity: str
    tail_position: int
    tail_hash: str
    snapshot_id: str
    actor_id: str
    authority_grant_id: str
    result_hash: str
    source_root: str = ""
    code_roots: list[str] = field(default_factory=list)
    schema_root: str = ""
    source_snapshot_hash: str = ""
    target_manifest_bytes_sha256: str = ""
    expected_output_sha256: str = ""
    origin_witness_path: str = ""
    origin_witness_sha256: str = ""
    origin_initial_control_root: str = ""
    origin_initial_physical_root_identity: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"verified", "diagnostic_only"}:
            raise ValueError("invalid restore preflight status")
        predicates_empty = not self.failed_predicates
        if (self.status == "verified") != predicates_empty:
            raise ValueError("restore preflight status must match failed predicates")
        if len(set(self.failed_predicates)) != len(self.failed_predicates):
            raise ValueError("restore preflight failed predicates must be unique")


@dataclass(frozen=True, slots=True)
class RestoreBoundFile:
    """One exact regular file observed by the full restore preflight."""

    relative_path: str
    raw_sha256: str
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class RestoreBoundArtefact:
    """One receipt-bound artefact and its exact manifest observation."""

    artefact_id: str
    relative_path: str
    artefact_sha256: str
    observation_sha256: str


@dataclass(frozen=True, slots=True)
class RestoreAdmissionClosure:
    """Immutable checked-input closure for the bounded locked recheck."""

    target_root: str
    snapshot: RestoreBoundFile
    endpoint_ownership: RestoreBoundFile
    artefact_manifest: RestoreBoundFile
    artefacts: tuple[RestoreBoundArtefact, ...]
    registry: object
    registry_state_sha256: str


@dataclass(frozen=True, slots=True)
class RestoreAdmissionBundle:
    """Full preflight result plus its immutable checked-input closure."""

    result: RestorePreflightResult
    closure: RestoreAdmissionClosure | None


class _RestorePreflightWithClosure(RestorePreflightResult):
    """API-compatible result carrying non-serialized admission state."""

    __slots__ = ("_admission_closure",)


def restore_admission_bundle_for_result(result: RestorePreflightResult) -> RestoreAdmissionBundle:
    """Recover the checked-input bundle carried by a full verifier result."""
    return RestoreAdmissionBundle(
        result=result,
        closure=getattr(result, "_admission_closure", None),
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value.resolve(strict=False))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(item) for item in value), key=canonical_bytes)
    return value


def _registry_state_sha256(registry: object) -> str:
    fields = getattr(registry, "__dataclass_fields__", None)
    if not isinstance(fields, dict):
        raise ArsError("restore registry does not expose immutable state")
    try:
        state = {name: _jsonable(getattr(registry, name)) for name in fields}
        return sha256_hex(canonical_bytes(state))
    except (TypeError, ValueError) as exc:
        raise ArsError("restore registry state is not canonical") from exc


def _strict_relative_path(root: Path, path: Path) -> tuple[Path, str]:
    target = root.resolve(strict=False)
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ArsError("restore input path must be absolute")
    try:
        relative = candidate.relative_to(target)
    except ValueError as exc:
        raise ArsError("restore input path escapes target root") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ArsError("restore input path is not canonical")
    if "\\" in relative.as_posix():
        raise ArsError("restore input path is not canonical")

    current = target
    for part in relative.parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise ArsError("restore input path is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ArsError("restore input path crosses a reparse point")
    if not stat.S_ISREG(metadata.st_mode):
        raise ArsError("restore input path is not a regular file")
    return current, relative.as_posix()


def _read_bound_json(root: Path, path: Path) -> tuple[dict[str, Any] | None, RestoreBoundFile | None]:
    try:
        current, relative = _strict_relative_path(root, path)
        data = current.read_bytes()
        value = json.loads(data.decode("utf-8"))
    except (ArsError, OSError, UnicodeError, json.JSONDecodeError):
        return None, None
    if not isinstance(value, dict):
        return None, None
    return value, RestoreBoundFile(
        relative_path=relative,
        raw_sha256=sha256_hex(data),
        canonical_sha256=sha256_hex(canonical_bytes(value)),
    )


def _read_bound_bytes(root: Path, relative_path: str) -> tuple[bytes, str, tuple[int, int]]:
    if not isinstance(relative_path, str) or "\\" in relative_path:
        raise ArsError("restore artefact path is not canonical")
    relative = Path(relative_path)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ArsError("restore artefact path is not canonical")
    current, canonical_relative = _strict_relative_path(root, root / relative)
    metadata = os.stat(current)
    return current.read_bytes(), canonical_relative, (metadata.st_dev, metadata.st_ino)


def _hash_without(value: object, field: str) -> str:
    payload = asdict(value)
    payload[field] = ""
    return sha256_hex(canonical_bytes(_jsonable(payload)))


def seal_backup_receipt(receipt: BackupReceipt) -> BackupReceipt:
    """Return a backup receipt with its canonical content hash populated."""
    if receipt.receipt_revision < 1:
        raise ValueError("backup receipt revision must be positive")
    return replace(receipt, receipt_hash=_hash_without(receipt, "receipt_hash"))


_BACKUP_PREPARATION_PATH = Path("manifests/backup-preparation.json")
_BACKUP_RECEIPT_PATH = Path("manifests/backup-receipt.json")
_BACKUP_ARTEFACT_MANIFEST_PATH = Path("manifests/external-artefacts.json")
_SHA256_CHARS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class _DerivedBackup:
    manifest: dict[str, Any]
    manifest_sha256: str
    source_file_bindings: tuple[dict[str, str], ...]
    snapshot: dict[str, Any]
    snapshot_sha256: str
    event_payload: dict[str, Any]
    external_command_rows: tuple[dict[str, Any], ...]
    external_manifest: dict[str, Any]
    external_manifest_sha256: str
    availability_observation_sha256: str


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256_CHARS


def _require_utc_timestamp(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ArsError(f"{label} must be an exact UTC timestamp")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as exc:
        raise ArsError(f"{label} must be an exact UTC timestamp") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ArsError(f"{label} must be an exact UTC timestamp")
    return value


def _canonical_backup_root(path: Path, label: str, *, require_exists: bool) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ArsError(f"backup {label} root must be absolute")
    try:
        resolved = _require_physical_path(candidate, require_exists=require_exists)
    except (IntegrityError, OSError) as exc:
        raise ArsError(f"backup {label} root is not a physical path") from exc
    if require_exists and not resolved.is_dir():
        raise ArsError(f"backup {label} root must be an existing directory")
    if not require_exists and resolved.exists() and not resolved.is_dir():
        raise ArsError(f"backup {label} root must be a directory")
    return resolved


def _require_backup_roots_disjoint(*roots: Path) -> None:
    for index, left in enumerate(roots):
        for right in roots[index + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise ConflictError("backup Source, destination, and stage roots must be disjoint")
            if left.exists() and right.exists():
                _require_physical_disjoint(
                    left,
                    right,
                    message="backup Source, destination, and stage roots must be physically disjoint",
                )


def _read_physical_regular_file(path: Path, label: str) -> bytes:
    try:
        resolved = _require_physical_path(path, require_exists=True)
        metadata = resolved.lstat()
    except (IntegrityError, OSError) as exc:
        raise ArsError(f"{label} is unavailable") from exc
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if not stat.S_ISREG(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
        raise ArsError(f"{label} must be a physical regular file")
    try:
        return resolved.read_bytes()
    except OSError as exc:
        raise ArsError(f"{label} is unavailable") from exc


def _remove_failed_exclusive(
    path: Path,
    created_identity: os.stat_result,
    label: str,
) -> None:
    try:
        visible = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ArsError(f"backup {label} failed path cannot be inspected") from exc
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISREG(visible.st_mode)
        or getattr(visible, "st_file_attributes", 0) & reparse_attribute
        or not os.path.samestat(visible, created_identity)
    ):
        raise ConflictError(f"backup {label} failed path changed identity")
    try:
        path.unlink()
    except OSError as exc:
        raise ArsError(f"backup {label} failed path cannot be removed") from exc
    if not _fsync_directory(path.parent):
        raise ArsError(f"backup {label} cleanup requires directory durability")


def _write_durable_exclusive(path: Path, data: bytes, label: str) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
        )
    except FileExistsError as exc:
        raise ConflictError(f"backup {label} already exists") from exc
    created_identity = os.fstat(descriptor)
    failure: BaseException | None = None
    try:
        remaining = memoryview(data)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("backup file write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except BaseException as exc:
        failure = exc
    try:
        os.close(descriptor)
    except BaseException as exc:
        if failure is None:
            failure = exc
    if failure is not None:
        try:
            _remove_failed_exclusive(path, created_identity, label)
        except (ArsError, ConflictError) as cleanup_error:
            raise cleanup_error from failure
        raise failure


def _fsync_physical_regular_file(path: Path, label: str) -> None:
    descriptor = -1
    try:
        resolved = _require_physical_path(path, require_exists=True)
        flags = os.O_RDWR | getattr(os, "O_BINARY", 0)
        descriptor = os.open(resolved, flags)
        opened = os.fstat(descriptor)
        visible = resolved.lstat()
        reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if (
            not stat.S_ISREG(opened.st_mode)
            or getattr(visible, "st_file_attributes", 0) & reparse_attribute
            or not os.path.samestat(opened, visible)
        ):
            raise IntegrityError(f"{label} is not a stable physical regular file")
        os.fsync(descriptor)
    except (IntegrityError, OSError) as exc:
        raise ArsError(f"{label} file durability is unavailable") from exc
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _remove_owned_incomplete_stage(
    root: Path,
    created_identity: os.stat_result,
) -> None:
    try:
        visible_root = root.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ArsError("incomplete backup stage cannot be inspected") from exc
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISDIR(visible_root.st_mode)
        or getattr(visible_root, "st_file_attributes", 0) & reparse_attribute
        or not os.path.samestat(visible_root, created_identity)
    ):
        raise ConflictError("incomplete backup stage changed identity")

    directories: list[tuple[Path, os.stat_result]] = []
    files: list[tuple[Path, os.stat_result]] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            children = tuple(directory.iterdir())
        except OSError as exc:
            raise ArsError("incomplete backup stage cannot be enumerated") from exc
        for child in children:
            try:
                metadata = child.lstat()
            except OSError as exc:
                raise ArsError("incomplete backup stage entry cannot be inspected") from exc
            if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
                raise ConflictError("incomplete backup stage contains a reparse point")
            if stat.S_ISDIR(metadata.st_mode):
                directories.append((child, metadata))
                stack.append(child)
            elif stat.S_ISREG(metadata.st_mode):
                files.append((child, metadata))
            else:
                raise ConflictError("incomplete backup stage contains an unsupported entry")

    try:
        for path, observed in files:
            if not os.path.samestat(path.lstat(), observed):
                raise ConflictError("incomplete backup stage file changed identity")
            path.unlink()
        for path, observed in sorted(
            directories,
            key=lambda item: len(item[0].parts),
            reverse=True,
        ):
            if not os.path.samestat(path.lstat(), observed):
                raise ConflictError("incomplete backup stage directory changed identity")
            path.rmdir()
        if not os.path.samestat(root.lstat(), created_identity):
            raise ConflictError("incomplete backup stage changed identity")
        root.rmdir()
    except (ConflictError, OSError) as exc:
        raise ArsError("incomplete backup stage cannot be removed safely") from exc
    if not _fsync_directory(root.parent):
        raise ArsError("incomplete backup stage cleanup requires parent durability")


def _file_binding(path: Path, root: Path) -> dict[str, str]:
    relative = path.relative_to(root).as_posix()
    return {"relative_path": relative, "raw_sha256": sha256_hex(path.read_bytes())}


def _iter_physical_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise ArsError("backup candidate tree is unavailable") from exc
        for child in children:
            try:
                metadata = child.lstat()
            except OSError as exc:
                raise ArsError("backup candidate entry is unavailable") from exc
            reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
                raise ArsError("backup candidate cannot contain a reparse point")
            if stat.S_ISDIR(metadata.st_mode):
                stack.append(child)
            elif stat.S_ISREG(metadata.st_mode):
                files.append(child)
            else:
                raise ArsError("backup candidate can contain only regular files and directories")
    return tuple(sorted(files, key=lambda item: item.relative_to(root).as_posix()))


def _is_mutable_store_residue(relative: Path) -> bool:
    if relative.parts and relative.parts[0] == "runtime":
        return True
    name = relative.name
    return name == "writer.lock" or name.endswith(".tmp") or ".tmp." in name


def _capture_source_store_bindings(source: Path) -> tuple[dict[str, str], ...]:
    bindings: list[dict[str, str]] = []
    for source_path in _iter_physical_files(source):
        relative = source_path.relative_to(source)
        if _is_mutable_store_residue(relative):
            continue
        data = _read_physical_regular_file(source_path, "backup Source file")
        bindings.append(
            {
                "relative_path": relative.as_posix(),
                "raw_sha256": sha256_hex(data),
            }
        )
    return tuple(bindings)


def _copy_source_store(source: Path, stage: Path) -> tuple[dict[str, str], ...]:
    source_bindings: list[dict[str, str]] = []
    for directory in ("objects", "events", "manifests", "receipts", "snapshots", "runtime"):
        (stage / directory).mkdir(parents=True, exist_ok=False)
    for source_path in _iter_physical_files(source):
        relative = source_path.relative_to(source)
        if _is_mutable_store_residue(relative):
            continue
        data = _read_physical_regular_file(source_path, "backup Source file")
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_durable_exclusive(target, data, "Source copy")
        source_bindings.append(
            {
                "relative_path": relative.as_posix(),
                "raw_sha256": sha256_hex(data),
            }
        )
    return tuple(source_bindings)


def _revalidate_source_bindings(source: Path, bindings: tuple[dict[str, str], ...]) -> None:
    for binding in bindings:
        path = source / Path(binding["relative_path"])
        current = _read_physical_regular_file(path, "backup Source file")
        if sha256_hex(current) != binding["raw_sha256"]:
            raise IntegrityError("backup Source changed while the candidate was prepared")


def _flush_tree(root: Path) -> None:
    directories = [path for path in root.rglob("*") if path.is_dir()]
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        if not _fsync_directory(directory):
            raise ArsError("backup candidate requires directory durability")
    if not _fsync_directory(root):
        raise ArsError("backup candidate requires directory durability")


def _flush_candidate_visibility(root: Path) -> None:
    for path in _iter_physical_files(root):
        _fsync_physical_regular_file(path, "backup candidate")
    _flush_tree(root)
    if not _fsync_directory(root.parent):
        raise ArsError("backup candidate directory entry requires parent durability")


def _rename_directory_no_replace(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ConflictError("backup destination already exists")
    if os.name == "nt":
        try:
            os.rename(source, destination)
        except FileExistsError as exc:
            raise ConflictError("backup destination already exists") from exc
        except OSError as exc:
            if getattr(exc, "winerror", None) in {5, 80, 183} and destination.exists():
                raise ConflictError("backup destination already exists") from exc
            raise ArsError("backup candidate publication failed") from exc
        return
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise ArsError("backup no-replace rename is unavailable")
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        if renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1) != 0:
            error = ctypes.get_errno()
            if error in {errno.EEXIST, errno.ENOTEMPTY}:
                raise ConflictError("backup destination already exists")
            raise OSError(error, os.strerror(error), str(destination))
        return
    raise ArsError("backup no-replace rename is unavailable on this platform")


@dataclass(frozen=True, slots=True)
class BackupMaterializer:
    """Prepare hidden backup bytes and publish them only after BackupCreated."""

    command_id: str
    source_root: Path
    destination_root: Path
    stage_root: Path
    receipt_id: str
    receipt_revision: int
    registry: object
    artefacts: tuple[BackupArtefactInput, ...]
    verified_at: str
    verified_by_actor_id: str
    verification_authority_grant_id: str
    approved_witness: StoreOriginWitness
    approved_witness_path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, str) or not self.command_id:
            raise ArsError("backup command identity is required")
        source = _canonical_backup_root(self.source_root, "Source", require_exists=True)
        destination = _canonical_backup_root(self.destination_root, "destination", require_exists=False)
        stage = _canonical_backup_root(self.stage_root, "stage", require_exists=False)
        expected_stage = destination.parent / f".{destination.name}.{self.command_id}.stage"
        if stage != expected_stage:
            raise ArsError("backup stage root is not the deterministic hidden destination sibling")
        _require_backup_roots_disjoint(source, destination, stage)
        object.__setattr__(self, "source_root", source)
        object.__setattr__(self, "destination_root", destination)
        object.__setattr__(self, "stage_root", stage)
        object.__setattr__(self, "artefacts", tuple(self.artefacts))
        try:
            validate_id(self.receipt_id, "backup_receipt")
        except (AttributeError, TypeError, ValueError) as exc:
            raise ArsError("backup receipt identity must be canonical") from exc
        if (
            not isinstance(self.receipt_revision, int)
            or isinstance(self.receipt_revision, bool)
            or self.receipt_revision < 1
        ):
            raise ArsError("backup receipt revision must be positive")
        _require_utc_timestamp(self.verified_at, "backup verification time")
        if not self.verified_by_actor_id or not self.verification_authority_grant_id:
            raise ArsError("backup verifier authority binding is required")
        if not isinstance(self.approved_witness, StoreOriginWitness):
            raise ArsError("backup Source requires an approved origin witness")
        if not self.approved_witness_path.is_absolute():
            raise ArsError("backup Source witness path must be absolute")
        validated_witness_path, _origin_root = validate_approved_origin_witness_path(
            self.approved_witness_path,
            self.approved_witness,
        )
        object.__setattr__(self, "approved_witness_path", validated_witness_path)
        artefact_ids: set[str] = set()
        for artefact in self.artefacts:
            if not isinstance(artefact, BackupArtefactInput):
                raise TypeError("backup artefacts must be BackupArtefactInput values")
            try:
                validate_id(artefact.artefact_id, "artefact")
            except (AttributeError, TypeError, ValueError) as exc:
                raise ArsError("backup artefact identity must be canonical") from exc
            if artefact.artefact_id in artefact_ids:
                raise ArsError("backup artefact identities must be unique")
            artefact_ids.add(artefact.artefact_id)
            if not artefact.source_path.is_absolute():
                raise ArsError("backup artefact source paths must be absolute")
            if not _is_sha256(artefact.content_sha256):
                raise ArsError("backup artefact content digest must be a lowercase SHA-256")
            if artefact.availability != "available":
                raise ArsError("backup materialization requires every external artefact to be available")
            if (
                not artefact.availability_evidence_refs
                or len(set(artefact.availability_evidence_refs)) != len(artefact.availability_evidence_refs)
                or any(not isinstance(item, str) or not item for item in artefact.availability_evidence_refs)
            ):
                raise ArsError("backup artefact availability evidence must be non-empty and unique")
            _require_utc_timestamp(artefact.observed_at, "backup artefact observation time")
        if not self.artefacts:
            raise ArsError("backup materialization requires at least one external artefact")
        fields = getattr(self.registry, "__dataclass_fields__", None)
        if not isinstance(fields, dict):
            raise ArsError("backup evidence registry must expose immutable state")
        registry_hash = getattr(self.registry, "registry_hash", None)
        if not _is_sha256(registry_hash):
            raise ArsError("backup evidence registry hash must be a lowercase SHA-256")
        try:
            checked = set(self.registry.checked_locations())
        except (AttributeError, TypeError, ValueError) as exc:
            raise ArsError("backup evidence registry topology is invalid") from exc
        if not {source, destination, stage}.issubset(checked):
            raise ArsError("backup Source, destination, and stage must all be registered")
        try:
            primary_root = self.registry.primary_root.resolve(strict=False)
            staging_root = self.registry.staging_root.resolve(strict=False)
            backup_roots = {root.resolve(strict=False) for root in self.registry.backup_roots}
        except (AttributeError, TypeError, ValueError) as exc:
            raise ArsError("backup evidence registry roles are invalid") from exc
        if primary_root != source or staging_root != stage or destination not in backup_roots:
            raise ArsError("backup evidence registry roles do not match the requested roots")
        if getattr(self.registry, "unregistered_replicas_prohibited", None) is not True:
            raise ArsError("backup evidence registry must prohibit unregistered replicas")
        verifier_bindings = getattr(self.registry, "verifier_authority_bindings", ())
        if (self.verified_by_actor_id, self.verification_authority_grant_id) not in verifier_bindings:
            raise ArsError("backup verifier authority is not registered")

    def derive_event_payload(
        self,
        *,
        snapshot_id: str,
        destination_class: str,
        schema_versions: tuple[str, ...],
        tool_versions: tuple[str, ...],
        encryption_class: str,
        redaction_class: str,
        ledger_snapshot: LedgerSnapshot,
    ) -> dict[str, Any]:
        """Derive the exact CreateBackup payload without writing any path."""
        self._snapshot_relative_path(snapshot_id)
        requested = {
            "snapshot_id": snapshot_id,
            "destination_class": destination_class,
            "schema_versions": list(schema_versions),
            "tool_versions": list(tool_versions),
            "encryption_class": encryption_class,
            "redaction_class": redaction_class,
        }
        existing_root = self._existing_candidate_root()
        if existing_root is not None:
            record, _raw = self._load_preparation(existing_root)
            self._validate_preparation_constructor(record)
            self._require_requested_policy(record["event_payload"], requested)
            self._verify_bound_files(existing_root, record, receipt_optional=True)
            return dict(record["event_payload"])
        derived = self._derive(
            snapshot_id=snapshot_id,
            destination_class=destination_class,
            schema_versions=schema_versions,
            tool_versions=tool_versions,
            encryption_class=encryption_class,
            redaction_class=redaction_class,
            ledger_snapshot=ledger_snapshot,
        )
        return dict(derived.event_payload)

    def prepare(self, command: Command, ledger_snapshot: LedgerSnapshot) -> BackupPreparation:
        """Create or exact-compare the hidden durable pre-event candidate."""
        self._validate_command_identity(command)
        payload = command.envelope.get("payload")
        if not isinstance(payload, dict):
            raise ArsError("CreateBackup payload must be an object")
        requested = self._requested_policy_from_payload(payload)
        expected_payload = self.derive_event_payload(
            **requested,
            ledger_snapshot=ledger_snapshot,
        )
        if payload != expected_payload:
            raise IntegrityError("CreateBackup payload differs from the exact Source observations")
        if self.destination_root.exists():
            raise ConflictError("backup destination already exists")
        if self.stage_root.exists():
            record, raw = self._load_preparation(self.stage_root)
            self._validate_preparation_command(record, command)
            self._verify_bound_files(self.stage_root, record, receipt_optional=False)
            source_bindings = self._validated_source_file_bindings(
                self.stage_root,
                record,
            )
            freshly_derived = self._derive(
                **requested,
                ledger_snapshot=ledger_snapshot,
            )
            if freshly_derived.source_file_bindings != source_bindings:
                raise IntegrityError("backup Source changed after the candidate was prepared")
            self._validate_preparation_derivation(record, freshly_derived)
            if _capture_source_store_bindings(self.source_root) != source_bindings:
                raise IntegrityError("backup Source changed after the candidate was prepared")
            _flush_candidate_visibility(self.stage_root)
            return BackupPreparation(
                command_id=self.command_id,
                stage_root=self.stage_root,
                destination_root=self.destination_root,
                preparation_sha256=sha256_hex(raw),
                event_payload=dict(record["event_payload"]),
            )

        derived = self._derive(**requested, ledger_snapshot=ledger_snapshot)
        try:
            self.stage_root.mkdir()
        except FileExistsError as exc:
            raise ConflictError("backup stage collision") from exc
        try:
            stage_identity = self.stage_root.lstat()
        except OSError as exc:
            raise ArsError("backup stage identity is unavailable") from exc
        preparation_durable = False
        try:
            source_bindings = _copy_source_store(self.source_root, self.stage_root)
            if source_bindings != derived.source_file_bindings:
                raise IntegrityError("backup Source files changed while the candidate was prepared")
            snapshot_path = self.stage_root / self._snapshot_relative_path(payload["snapshot_id"])
            self._write_exact_or_compare(snapshot_path, canonical_bytes(derived.snapshot), "snapshot")
            external_root = self.stage_root / "external-artefacts"
            external_root.mkdir(exist_ok=False)
            for artefact in sorted(self.artefacts, key=lambda item: item.artefact_id):
                data = _read_physical_regular_file(artefact.source_path, "backup external artefact")
                if sha256_hex(data) != artefact.content_sha256:
                    raise IntegrityError("backup external artefact differs from its approved content digest")
                self._write_exact_or_compare(external_root / artefact.artefact_id, data, "external artefact")
            self._write_exact_or_compare(
                self.stage_root / _BACKUP_ARTEFACT_MANIFEST_PATH,
                canonical_bytes(derived.external_manifest),
                "external artefact manifest",
            )
            _revalidate_source_bindings(self.source_root, source_bindings)
            rederived = self._derive(**requested, ledger_snapshot=ledger_snapshot)
            if rederived != derived:
                raise IntegrityError("backup Source observations changed while the candidate was prepared")
            file_bindings = tuple(
                _file_binding(path, self.stage_root) for path in _iter_physical_files(self.stage_root)
            )
            record = self._preparation_record(command, derived, file_bindings)
            preparation_raw = canonical_bytes(record)
            _write_durable_exclusive(
                self.stage_root / _BACKUP_PREPARATION_PATH,
                preparation_raw,
                "preparation record",
            )
            preparation_durable = True
            _flush_candidate_visibility(self.stage_root)
            if self.destination_root.exists():
                raise ConflictError("backup destination appeared during preparation")
            self._verify_bound_files(self.stage_root, record, receipt_optional=False)
            return BackupPreparation(
                command_id=self.command_id,
                stage_root=self.stage_root,
                destination_root=self.destination_root,
                preparation_sha256=sha256_hex(preparation_raw),
                event_payload=dict(derived.event_payload),
            )
        except BaseException as exc:
            if not preparation_durable:
                try:
                    _remove_owned_incomplete_stage(self.stage_root, stage_identity)
                except (ArsError, ConflictError) as cleanup_error:
                    raise cleanup_error from exc
            raise

    def materialize(self, command: Command, committed_event: Mapping[str, Any]) -> BackupReceipt:
        """Publish the exact prepared bytes after their BackupCreated event."""
        self._validate_command_identity(command)
        if self.stage_root.exists() and self.destination_root.exists():
            raise ConflictError("backup stage and destination both exist")
        root = self.destination_root if self.destination_root.exists() else self.stage_root
        if not root.exists():
            raise ArsError("backup has no prepared candidate to materialize")
        record, _raw = self._load_preparation(root)
        self._validate_preparation_command(record, command)
        self._validate_committed_event(record, command, committed_event)
        self._verify_bound_files(root, record, receipt_optional=True)
        self._validate_committed_candidate(root, record, committed_event)
        receipt = self._receipt(record, command, committed_event)
        receipt_raw = canonical_bytes(_jsonable(asdict(receipt)))
        if root == self.destination_root:
            existing = _read_physical_regular_file(root / _BACKUP_RECEIPT_PATH, "backup receipt")
            if existing != receipt_raw:
                raise ConflictError("backup destination receipt differs from the committed event")
            _flush_candidate_visibility(root)
            return receipt

        receipt_path = root / _BACKUP_RECEIPT_PATH
        if receipt_path.exists():
            if _read_physical_regular_file(receipt_path, "backup receipt") != receipt_raw:
                raise ConflictError("backup stage receipt differs from the committed event")
        else:
            _write_durable_exclusive(receipt_path, receipt_raw, "receipt")
            if not _fsync_directory(receipt_path.parent):
                raise ArsError("backup receipt requires directory durability")
        _flush_candidate_visibility(root)
        self._validate_committed_event(record, command, committed_event)
        self._validate_committed_candidate(root, record, committed_event)
        if self.destination_root.exists():
            raise ConflictError("backup destination appeared before publication")
        _rename_directory_no_replace(self.stage_root, self.destination_root)
        if not _fsync_directory(self.destination_root.parent):
            raise ArsError("backup destination publication requires directory durability")
        self._verify_bound_files(self.destination_root, record, receipt_optional=True)
        self._validate_committed_candidate(self.destination_root, record, committed_event)
        if (
            _read_physical_regular_file(
                self.destination_root / _BACKUP_RECEIPT_PATH,
                "backup receipt",
            )
            != receipt_raw
        ):
            raise IntegrityError("published backup receipt changed")
        return receipt

    def _existing_candidate_root(self) -> Path | None:
        stage_exists = self.stage_root.exists()
        destination_exists = self.destination_root.exists()
        if stage_exists and destination_exists:
            raise ConflictError("backup stage and destination both exist")
        if destination_exists:
            return self.destination_root
        if stage_exists:
            return self.stage_root
        return None

    def _derive(
        self,
        *,
        snapshot_id: str,
        destination_class: str,
        schema_versions: tuple[str, ...],
        tool_versions: tuple[str, ...],
        encryption_class: str,
        redaction_class: str,
        ledger_snapshot: LedgerSnapshot,
    ) -> _DerivedBackup:
        if not isinstance(ledger_snapshot, LedgerSnapshot):
            raise TypeError("backup derivation requires a LedgerSnapshot")
        if not isinstance(snapshot_id, str) or not snapshot_id:
            raise ArsError("backup snapshot identity is required")
        for label, value in (
            ("destination class", destination_class),
            ("encryption class", encryption_class),
            ("redaction class", redaction_class),
        ):
            if not isinstance(value, str) or not value:
                raise ArsError(f"backup {label} is required")
        schemas_tuple = self._nonempty_unique_strings(schema_versions, "schema versions")
        tools_tuple = self._nonempty_unique_strings(tool_versions, "tool versions")
        try:
            manifest_raw = (self.source_root / "manifests" / "store-identity.json").read_bytes()
            manifest = load_store_manifest(
                self.source_root,
                approved_witness=self.approved_witness,
                approved_witness_path=self.approved_witness_path,
            )
        except (ArsError, IntegrityError, OSError) as exc:
            raise IntegrityError("backup Source identity is invalid") from exc
        project_id = str(manifest.get("project_id", ""))
        store_identity = str(manifest.get("store_identity", ""))
        code_roots = manifest.get("code_roots")
        if not isinstance(code_roots, list) or not code_roots or not all(isinstance(item, str) for item in code_roots):
            raise IntegrityError("backup Source code-root binding is invalid")
        require_existing_control_root([Path(item) for item in code_roots], self.source_root)
        if manifest.get("control_root") != str(self.source_root):
            raise IntegrityError("backup Source manifest is bound to a different root")
        if project_id != self.approved_witness.project_id or store_identity != self.approved_witness.store_identity:
            raise IntegrityError("backup Source differs from the approved origin witness")
        schemas = bundled_runtime_schema_registry()
        current = EventLedger(self.source_root, project_id, schemas).snapshot()
        if (
            current.events != ledger_snapshot.events
            or current.global_position != ledger_snapshot.global_position
            or current.event_hash != ledger_snapshot.event_hash
            or dict(current.stream_versions) != dict(ledger_snapshot.stream_versions)
            or current.fingerprint != ledger_snapshot.fingerprint
        ):
            raise IntegrityError("backup ledger snapshot is not the current Source ledger")
        resolver = LedgerAuthorityGrantResolver(
            self.source_root,
            project_id,
            store_identity,
            schemas,
            approved_witness=self.approved_witness,
            approved_witness_path=self.approved_witness_path,
        )
        state = replay(
            ledger_snapshot.events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
        source_file_bindings = _capture_source_store_bindings(self.source_root)
        snapshot = {
            "snapshot_id": snapshot_id,
            "source_position": ledger_snapshot.global_position,
            "source_hash": ledger_snapshot.event_hash,
            "state_hash": sha256_hex(canonical_bytes(state)),
            "source_file_bindings_sha256": sha256_hex(canonical_bytes(list(source_file_bindings))),
            "replay_start_position": 1,
            "replay_end_position": ledger_snapshot.global_position,
            "schema_versions": list(schemas_tuple),
            "tool_versions": list(tools_tuple),
        }
        snapshot_raw = canonical_bytes(snapshot)
        command_rows: list[dict[str, Any]] = []
        manifest_rows: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        for artefact in sorted(self.artefacts, key=lambda item: item.artefact_id):
            data = _read_physical_regular_file(artefact.source_path, "backup external artefact")
            if sha256_hex(data) != artefact.content_sha256:
                raise IntegrityError("backup external artefact differs from its approved content digest")
            command_rows.append(
                {
                    "artefact_id": artefact.artefact_id,
                    "content_sha256": artefact.content_sha256,
                    "availability": artefact.availability,
                    "availability_evidence_refs": list(artefact.availability_evidence_refs),
                }
            )
            observation = {
                "artefact_id": artefact.artefact_id,
                "artefact_hash": artefact.content_sha256,
                "availability_status": artefact.availability,
                "observed_at": artefact.observed_at,
                "authority_grant_id": self.verification_authority_grant_id,
            }
            observations.append(observation)
            manifest_rows.append(
                {
                    **observation,
                    "relative_path": f"external-artefacts/{artefact.artefact_id}",
                    "availability_evidence_refs": list(artefact.availability_evidence_refs),
                }
            )
        external_manifest = {"artefacts": manifest_rows}
        event_payload = {
            "project_id": project_id,
            "store_identity": store_identity,
            "canonical_tail_position": ledger_snapshot.global_position,
            "canonical_tail_sha256": ledger_snapshot.event_hash,
            "snapshot_id": snapshot_id,
            "snapshot_sha256": sha256_hex(snapshot_raw),
            "replay_start_position": 1,
            "replay_end_position": ledger_snapshot.global_position,
            "schema_versions": list(schemas_tuple),
            "tool_versions": list(tools_tuple),
            "encryption_class": encryption_class,
            "redaction_class": redaction_class,
            "external_artefacts": command_rows,
            "destination_class": destination_class,
        }
        return _DerivedBackup(
            manifest=dict(manifest),
            manifest_sha256=sha256_hex(manifest_raw),
            source_file_bindings=source_file_bindings,
            snapshot=snapshot,
            snapshot_sha256=sha256_hex(snapshot_raw),
            event_payload=event_payload,
            external_command_rows=tuple(command_rows),
            external_manifest=external_manifest,
            external_manifest_sha256=sha256_hex(canonical_bytes(external_manifest)),
            availability_observation_sha256=sha256_hex(canonical_bytes(observations)),
        )

    @staticmethod
    def _nonempty_unique_strings(values: tuple[str, ...], label: str) -> tuple[str, ...]:
        result = tuple(values)
        if (
            not result
            or len(set(result)) != len(result)
            or any(not isinstance(item, str) or not item for item in result)
        ):
            raise ArsError(f"backup {label} must be non-empty and unique")
        return result

    def _snapshot_relative_path(self, snapshot_id: object) -> Path:
        invalid_characters = '<>:"/\\|?*'
        if (
            not isinstance(snapshot_id, str)
            or not snapshot_id
            or snapshot_id in {".", ".."}
            or any(ord(character) < 32 for character in snapshot_id)
            or any(character in invalid_characters for character in snapshot_id)
            or snapshot_id.endswith((".", " "))
            or snapshot_id.split(".", 1)[0].rstrip(" .").upper() in _WINDOWS_RESERVED_FILENAMES
        ):
            raise ArsError("backup snapshot identity must be a safe single filename component")
        relative = Path("snapshots") / f"{snapshot_id}.json"
        snapshots_root = (self.stage_root / "snapshots").resolve(strict=False)
        candidate = (self.stage_root / relative).resolve(strict=False)
        if candidate.parent != snapshots_root:
            raise ArsError("backup snapshot identity must be a safe single filename component")
        return relative

    @staticmethod
    def _requested_policy_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return {
                "snapshot_id": payload["snapshot_id"],
                "destination_class": payload["destination_class"],
                "schema_versions": tuple(payload["schema_versions"]),
                "tool_versions": tuple(payload["tool_versions"]),
                "encryption_class": payload["encryption_class"],
                "redaction_class": payload["redaction_class"],
            }
        except (KeyError, TypeError) as exc:
            raise ArsError("CreateBackup payload lacks required materialization inputs") from exc

    @staticmethod
    def _require_requested_policy(event_payload: object, requested: dict[str, Any]) -> None:
        if not isinstance(event_payload, dict):
            raise IntegrityError("backup preparation event payload is invalid")
        for key, value in requested.items():
            expected = list(value) if key in {"schema_versions", "tool_versions"} else value
            if event_payload.get(key) != expected:
                raise ConflictError("backup request differs from the existing bound preparation")

    def _validate_command_identity(self, command: Command) -> None:
        if not isinstance(command, Command):
            raise TypeError("backup materializer requires a Command")
        envelope = command.envelope
        if (
            command.command_id != self.command_id
            or envelope.get("command_type") != "CreateBackup"
            or envelope.get("schema_id") != "ars://core/command/CreateBackup"
            or envelope.get("schema_version") != "1.0.0"
        ):
            raise ConflictError("backup command differs from the bound materializer")

    def _preparation_record(
        self,
        command: Command,
        derived: _DerivedBackup,
        file_bindings: tuple[dict[str, str], ...],
    ) -> dict[str, Any]:
        return {
            "schema_id": "ars://operations/backup-preparation",
            "schema_version": "1.0.0",
            "command_id": self.command_id,
            "project_id": derived.event_payload["project_id"],
            "source_root": str(self.source_root),
            "destination_root": str(self.destination_root),
            "stage_root": str(self.stage_root),
            "receipt_id": self.receipt_id,
            "receipt_revision": self.receipt_revision,
            "created_by_actor_id": command.actor_id,
            "submitted_at": command.envelope.get("submitted_at"),
            "verified_at": self.verified_at,
            "verified_by_actor_id": self.verified_by_actor_id,
            "verification_authority_grant_id": self.verification_authority_grant_id,
            "store_identity": derived.event_payload["store_identity"],
            "source_endpoint_scheme": derived.manifest.get("endpoint_scheme"),
            "source_manifest_sha256": derived.manifest_sha256,
            "source_file_bindings": list(derived.source_file_bindings),
            "pre_event_tail_position": derived.event_payload["canonical_tail_position"],
            "pre_event_tail_hash": derived.event_payload["canonical_tail_sha256"],
            "snapshot": derived.snapshot,
            "snapshot_sha256": derived.snapshot_sha256,
            "external_artefact_manifest_sha256": derived.external_manifest_sha256,
            "availability_observation_sha256": derived.availability_observation_sha256,
            "evidence_registry_hash": getattr(self.registry, "registry_hash"),
            "evidence_registry_state_sha256": _registry_state_sha256(self.registry),
            "origin_witness_path": str(self.approved_witness_path),
            "origin_witness_sha256": self.approved_witness.raw_sha256,
            "event_payload": derived.event_payload,
            "file_bindings": list(file_bindings),
        }

    @staticmethod
    def _write_exact_or_compare(path: Path, data: bytes, label: str) -> None:
        if path.exists():
            existing = _read_physical_regular_file(path, f"backup {label}")
            if existing != data:
                raise ConflictError(f"backup {label} conflicts with Source content")
            return
        _write_durable_exclusive(path, data, label)

    def _load_preparation(self, root: Path) -> tuple[dict[str, Any], bytes]:
        try:
            raw = _read_physical_regular_file(root / _BACKUP_PREPARATION_PATH, "backup preparation")
            value = json.loads(raw.decode("utf-8"))
        except (ArsError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConflictError("backup stage or destination has no canonical preparation") from exc
        if not isinstance(value, dict) or raw != canonical_bytes(value):
            raise ConflictError("backup stage or destination has no canonical preparation")
        return value, raw

    def _validate_preparation_constructor(self, record: dict[str, Any]) -> None:
        expected = {
            "command_id": self.command_id,
            "source_root": str(self.source_root),
            "destination_root": str(self.destination_root),
            "stage_root": str(self.stage_root),
            "receipt_id": self.receipt_id,
            "receipt_revision": self.receipt_revision,
            "verified_at": self.verified_at,
            "verified_by_actor_id": self.verified_by_actor_id,
            "verification_authority_grant_id": self.verification_authority_grant_id,
            "evidence_registry_hash": getattr(self.registry, "registry_hash"),
            "evidence_registry_state_sha256": _registry_state_sha256(self.registry),
            "origin_witness_path": str(self.approved_witness_path),
            "origin_witness_sha256": self.approved_witness.raw_sha256,
        }
        if record.get("schema_id") != "ars://operations/backup-preparation" or record.get("schema_version") != "1.0.0":
            raise ConflictError("backup stage or destination preparation schema differs")
        if any(record.get(key) != value for key, value in expected.items()):
            raise ConflictError("backup stage or destination belongs to a different request")

    def _validate_preparation_command(self, record: dict[str, Any], command: Command) -> None:
        self._validate_preparation_constructor(record)
        if (
            record.get("created_by_actor_id") != command.actor_id
            or record.get("submitted_at") != command.envelope.get("submitted_at")
            or record.get("project_id") != command.envelope.get("project_id")
            or record.get("event_payload") != command.envelope.get("payload")
            or record.get("store_identity") != command.envelope.get("payload", {}).get("store_identity")
        ):
            raise ConflictError("backup preparation differs from the CreateBackup command")

    def _validate_preparation_derivation(
        self,
        record: dict[str, Any],
        derived: _DerivedBackup,
    ) -> None:
        expected_fields = {
            "project_id": derived.event_payload["project_id"],
            "store_identity": derived.event_payload["store_identity"],
            "source_endpoint_scheme": derived.manifest.get("endpoint_scheme"),
            "source_manifest_sha256": derived.manifest_sha256,
            "source_file_bindings": list(derived.source_file_bindings),
            "pre_event_tail_position": derived.event_payload["canonical_tail_position"],
            "pre_event_tail_hash": derived.event_payload["canonical_tail_sha256"],
            "snapshot": derived.snapshot,
            "snapshot_sha256": derived.snapshot_sha256,
            "external_artefact_manifest_sha256": derived.external_manifest_sha256,
            "availability_observation_sha256": derived.availability_observation_sha256,
            "event_payload": derived.event_payload,
        }
        if any(record.get(key) != value for key, value in expected_fields.items()):
            raise IntegrityError("backup preparation differs from the freshly derived candidate")

        expected_bindings = {item["relative_path"]: item["raw_sha256"] for item in derived.source_file_bindings}
        additions = [
            (
                self._snapshot_relative_path(derived.event_payload["snapshot_id"]).as_posix(),
                derived.snapshot_sha256,
            ),
            (
                _BACKUP_ARTEFACT_MANIFEST_PATH.as_posix(),
                derived.external_manifest_sha256,
            ),
            *(
                (
                    (Path("external-artefacts") / artefact.artefact_id).as_posix(),
                    artefact.content_sha256,
                )
                for artefact in self.artefacts
            ),
        ]
        for relative, digest in additions:
            existing = expected_bindings.get(relative)
            if existing is not None and existing != digest:
                raise IntegrityError("backup freshly derived candidate has conflicting file bindings")
            expected_bindings[relative] = digest
        expected_file_bindings = [
            {"relative_path": relative, "raw_sha256": expected_bindings[relative]}
            for relative in sorted(expected_bindings)
        ]
        if record.get("file_bindings") != expected_file_bindings:
            raise IntegrityError("backup preparation file bindings differ from the freshly derived candidate")

    @staticmethod
    def _relative_binding_path(value: object) -> Path:
        if not isinstance(value, str) or "\\" in value:
            raise IntegrityError("backup file binding path is not canonical")
        relative = Path(value)
        if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
            raise IntegrityError("backup file binding path is not canonical")
        return relative

    def _verify_bound_files(self, root: Path, record: dict[str, Any], *, receipt_optional: bool) -> None:
        bindings = record.get("file_bindings")
        if not isinstance(bindings, list):
            raise IntegrityError("backup preparation file bindings are invalid")
        expected: dict[str, str] = {}
        for item in bindings:
            if not isinstance(item, dict) or set(item) != {"relative_path", "raw_sha256"}:
                raise IntegrityError("backup preparation file bindings are invalid")
            relative = self._relative_binding_path(item["relative_path"])
            digest = item["raw_sha256"]
            if not _is_sha256(digest) or relative.as_posix() in expected:
                raise IntegrityError("backup preparation file bindings are invalid")
            expected[relative.as_posix()] = digest
        preparation_name = _BACKUP_PREPARATION_PATH.as_posix()
        receipt_name = _BACKUP_RECEIPT_PATH.as_posix()
        actual_files = _iter_physical_files(root)
        actual_names = {path.relative_to(root).as_posix() for path in actual_files}
        permitted = set(expected) | {preparation_name}
        if receipt_optional:
            permitted.add(receipt_name)
        if actual_names - permitted or not set(expected).issubset(actual_names) or preparation_name not in actual_names:
            raise ConflictError("backup stage or destination exact file set differs")
        for relative, digest in expected.items():
            data = _read_physical_regular_file(root / Path(relative), "backup bound file")
            if sha256_hex(data) != digest:
                raise ConflictError("backup stage or destination file content differs")
        runtime = root / "runtime"
        if not runtime.is_dir() or any(runtime.iterdir()):
            raise ConflictError("backup runtime residue is not empty")

    def _validated_source_file_bindings(
        self,
        root: Path,
        record: dict[str, Any],
    ) -> tuple[dict[str, str], ...]:
        source_bindings = record.get("source_file_bindings")
        candidate_bindings = record.get("file_bindings")
        if not isinstance(source_bindings, list) or not isinstance(candidate_bindings, list):
            raise IntegrityError("backup Source file bindings are invalid")
        candidate_by_path: dict[str, str] = {}
        for item in candidate_bindings:
            if not isinstance(item, dict) or set(item) != {"relative_path", "raw_sha256"}:
                raise IntegrityError("backup Source file bindings are invalid")
            relative = self._relative_binding_path(item["relative_path"])
            digest = item["raw_sha256"]
            if not _is_sha256(digest):
                raise IntegrityError("backup Source file bindings are invalid")
            candidate_by_path[relative.as_posix()] = digest

        validated: list[dict[str, str]] = []
        previous_path: str | None = None
        for item in source_bindings:
            if not isinstance(item, dict) or set(item) != {"relative_path", "raw_sha256"}:
                raise IntegrityError("backup Source file bindings are invalid")
            relative = self._relative_binding_path(item["relative_path"])
            relative_name = relative.as_posix()
            digest = item["raw_sha256"]
            if (
                not _is_sha256(digest)
                or _is_mutable_store_residue(relative)
                or (previous_path is not None and relative_name <= previous_path)
            ):
                raise IntegrityError("backup Source file bindings are invalid")
            if candidate_by_path.get(relative_name) != digest:
                raise IntegrityError("backup Source file binding differs from the prepared candidate")
            try:
                data = _read_physical_regular_file(root / relative, "backup Source file")
            except ArsError as exc:
                raise IntegrityError("backup Source file is absent from the prepared candidate") from exc
            if sha256_hex(data) != digest:
                raise IntegrityError("backup Source file differs from the exact committed snapshot")
            validated.append({"relative_path": relative_name, "raw_sha256": digest})
            previous_path = relative_name
        return tuple(validated)

    def _validate_committed_event(
        self,
        record: dict[str, Any],
        command: Command,
        committed_event: Mapping[str, Any],
    ) -> None:
        event = dict(committed_event)
        expected = {
            "event_type": "BackupCreated",
            "schema_id": "ars://core/event/BackupCreated",
            "schema_version": "1.0.0",
            "project_id": record["project_id"],
            "stream_id": command.target_stream_id,
            "command_id": command.command_id,
            "command_type": "CreateBackup",
            "actor_id": command.actor_id,
            "authority_grant_id": command.envelope.get("authority_grant_id"),
            "idempotency_key": command.idempotency_key,
            "command_payload_hash": command.payload_hash,
            "correlation_id": command.envelope.get("correlation_id"),
            "causation_id": command.envelope.get("causation_id"),
            "payload": record["event_payload"],
            "global_position": record["pre_event_tail_position"] + 1,
            "previous_event_hash": record["pre_event_tail_hash"],
        }
        if any(event.get(key) != value for key, value in expected.items()):
            raise IntegrityError("BackupCreated event differs from the prepared candidate")
        recorded_hash = event.get("event_hash")
        unsigned = dict(event)
        unsigned.pop("event_hash", None)
        if recorded_hash != sha256_hex(canonical_bytes(unsigned)):
            raise IntegrityError("BackupCreated event hash is invalid")
        schemas = bundled_runtime_schema_registry()
        snapshot = EventLedger(self.source_root, record["project_id"], schemas).snapshot()
        matches = [item for item in snapshot.events if item.get("event_id") == event.get("event_id")]
        if len(matches) != 1 or matches[0] != event:
            raise IntegrityError("BackupCreated event is not committed in the Source ledger")

    def _validate_committed_candidate(
        self,
        root: Path,
        record: dict[str, Any],
        committed_event: Mapping[str, Any],
    ) -> None:
        """Join staged descriptors and bytes back to the committed event."""
        payload = committed_event.get("payload")
        if not isinstance(payload, dict):
            raise IntegrityError("BackupCreated payload is invalid")
        try:
            project_id = str(payload["project_id"])
            store_identity = str(payload["store_identity"])
            tail_position = int(payload["canonical_tail_position"])
            tail_hash = str(payload["canonical_tail_sha256"])
            snapshot_id = str(payload["snapshot_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("BackupCreated snapshot binding is invalid") from exc
        snapshot_relative = self._snapshot_relative_path(snapshot_id)
        source_file_bindings = self._validated_source_file_bindings(root, record)
        source_file_bindings_sha256 = sha256_hex(canonical_bytes(list(source_file_bindings)))

        manifest_path = root / "manifests" / "store-identity.json"
        manifest_raw = _read_physical_regular_file(manifest_path, "backup Source manifest")
        try:
            manifest = load_store_manifest_unbound(root)
        except (ArsError, IntegrityError, OSError) as exc:
            raise IntegrityError("backup candidate Source manifest is invalid") from exc
        if (
            manifest.get("project_id") != project_id
            or manifest.get("store_identity") != store_identity
            or manifest.get("control_root") != str(self.source_root)
            or manifest.get("endpoint_scheme") != record.get("source_endpoint_scheme")
            or sha256_hex(manifest_raw) != record.get("source_manifest_sha256")
            or sha256_hex(canonical_bytes(manifest)) != self.approved_witness.initial_manifest_sha256
        ):
            raise IntegrityError("backup candidate Source manifest differs from its approved witness")
        code_roots = manifest.get("code_roots")
        if not isinstance(code_roots, list) or not code_roots or not all(isinstance(item, str) for item in code_roots):
            raise IntegrityError("backup candidate Source code-root binding is invalid")
        require_existing_control_root([Path(item) for item in code_roots], root)

        schemas = bundled_runtime_schema_registry()
        candidate_ledger = EventLedger(root, project_id, schemas).snapshot()
        if candidate_ledger.global_position != tail_position or candidate_ledger.event_hash != tail_hash:
            raise IntegrityError("backup candidate ledger differs from the committed pre-event tail")
        resolver = LedgerAuthorityGrantResolver(
            root,
            project_id,
            store_identity,
            schemas,
            approved_witness=self.approved_witness,
            approved_witness_path=self.approved_witness_path,
            restore_source_alias=True,
        )
        state = replay(
            candidate_ledger.events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
        expected_snapshot = {
            "snapshot_id": snapshot_id,
            "source_position": tail_position,
            "source_hash": tail_hash,
            "state_hash": sha256_hex(canonical_bytes(state)),
            "source_file_bindings_sha256": source_file_bindings_sha256,
            "replay_start_position": payload.get("replay_start_position"),
            "replay_end_position": payload.get("replay_end_position"),
            "schema_versions": payload.get("schema_versions"),
            "tool_versions": payload.get("tool_versions"),
        }
        snapshot_raw = _read_physical_regular_file(root / snapshot_relative, "backup snapshot")
        expected_snapshot_raw = canonical_bytes(expected_snapshot)
        if (
            record.get("pre_event_tail_position") != tail_position
            or record.get("pre_event_tail_hash") != tail_hash
            or record.get("project_id") != project_id
            or record.get("store_identity") != store_identity
            or record.get("snapshot") != expected_snapshot
            or record.get("snapshot_sha256") != payload.get("snapshot_sha256")
            or snapshot_raw != expected_snapshot_raw
            or sha256_hex(snapshot_raw) != payload.get("snapshot_sha256")
        ):
            raise IntegrityError("backup snapshot differs from the exact committed event")

        expected_command_rows: list[dict[str, Any]] = []
        expected_manifest_rows: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        for artefact in sorted(self.artefacts, key=lambda item: item.artefact_id):
            command_row = {
                "artefact_id": artefact.artefact_id,
                "content_sha256": artefact.content_sha256,
                "availability": artefact.availability,
                "availability_evidence_refs": list(artefact.availability_evidence_refs),
            }
            observation = {
                "artefact_id": artefact.artefact_id,
                "artefact_hash": artefact.content_sha256,
                "availability_status": artefact.availability,
                "observed_at": artefact.observed_at,
                "authority_grant_id": self.verification_authority_grant_id,
            }
            expected_command_rows.append(command_row)
            observations.append(observation)
            expected_manifest_rows.append(
                {
                    **observation,
                    "relative_path": f"external-artefacts/{artefact.artefact_id}",
                    "availability_evidence_refs": list(artefact.availability_evidence_refs),
                }
            )
            artefact_raw = _read_physical_regular_file(
                root / "external-artefacts" / artefact.artefact_id,
                "backup external artefact",
            )
            if sha256_hex(artefact_raw) != artefact.content_sha256:
                raise IntegrityError("backup external artefact differs from the exact committed event")
        expected_manifest = {"artefacts": expected_manifest_rows}
        manifest_bytes = _read_physical_regular_file(
            root / _BACKUP_ARTEFACT_MANIFEST_PATH,
            "backup external artefact manifest",
        )
        expected_manifest_bytes = canonical_bytes(expected_manifest)
        if (
            payload.get("external_artefacts") != expected_command_rows
            or manifest_bytes != expected_manifest_bytes
            or record.get("external_artefact_manifest_sha256") != sha256_hex(expected_manifest_bytes)
            or record.get("availability_observation_sha256") != sha256_hex(canonical_bytes(observations))
        ):
            raise IntegrityError("backup external artefact manifest differs from the exact committed event")

    def _receipt(
        self,
        record: dict[str, Any],
        command: Command,
        committed_event: Mapping[str, Any],
    ) -> BackupReceipt:
        payload = record["event_payload"]
        snapshot = record["snapshot"]
        bindings = tuple(
            ArtefactBinding(str(item["artefact_id"]), str(item["content_sha256"]))
            for item in payload["external_artefacts"]
        )
        receipt = BackupReceipt(
            receipt_id=self.receipt_id,
            receipt_revision=self.receipt_revision,
            receipt_hash="",
            project_id=record["project_id"],
            store_identity=record["store_identity"],
            canonical_tail_position=record["pre_event_tail_position"],
            canonical_tail_hash=record["pre_event_tail_hash"],
            snapshot_id=str(snapshot["snapshot_id"]),
            snapshot_hash=record["snapshot_sha256"],
            snapshot_source_position=int(snapshot["source_position"]),
            snapshot_source_hash=str(snapshot["source_hash"]),
            snapshot_state_hash=str(snapshot["state_hash"]),
            replay_start_position=int(snapshot["replay_start_position"]),
            replay_end_position=int(snapshot["replay_end_position"]),
            schema_versions=tuple(snapshot["schema_versions"]),
            tool_versions=tuple(snapshot["tool_versions"]),
            encryption_class=str(payload["encryption_class"]),
            redaction_class=str(payload["redaction_class"]),
            external_artefact_manifest_hash=record["external_artefact_manifest_sha256"],
            artefact_bindings=bindings,
            availability_status="available",
            availability_observation_hash=record["availability_observation_sha256"],
            created_at=str(committed_event["recorded_at"]),
            created_by_actor_id=command.actor_id,
            verified_at=self.verified_at,
            verified_by_actor_id=self.verified_by_actor_id,
            verification_authority_grant_id=self.verification_authority_grant_id,
            destination_class=str(payload["destination_class"]),
            source_endpoint_scheme=str(record["source_endpoint_scheme"]),
            evidence_registry_hash=str(record["evidence_registry_hash"]),
        )
        sealed = seal_backup_receipt(receipt)
        bundled_runtime_schema_registry().validate(
            "ars://operations/backup-receipt",
            _jsonable(asdict(sealed)),
        )
        return sealed


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, "0" * 64
    return (value if isinstance(value, dict) else None), sha256_hex(data)


def _inside(root: Path, relative: str) -> Path | None:
    target = (root / relative).resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    if target == resolved_root or resolved_root not in target.parents:
        return None
    return target


def verify_restore_before_writer_lease(
    *,
    target_root: Path,
    receipt: BackupReceipt,
    snapshot_path: Path,
    endpoint_ownership_path: Path,
    artefact_manifest_path: Path,
    registry: object,
    actor_id: str,
    authority_grant_id: str,
    approved_witness: StoreOriginWitness | None = None,
    approved_witness_path: Path | None = None,
    _capture_bundle: bool = False,
) -> RestorePreflightResult | RestoreAdmissionBundle:
    """Independently inspect a moved store and derive a pre-writer result."""
    target = target_root.resolve(strict=False)
    failed: list[str] = []
    validated_witness_path: Path | None = None
    origin_root: Path | None = None
    if approved_witness is None:
        failed.append("origin_witness_required")
    if approved_witness_path is None or not approved_witness_path.is_absolute():
        failed.append("origin_witness_path_required")
    elif approved_witness is not None:
        try:
            validated_witness_path, origin_root = validate_approved_origin_witness_path(
                approved_witness_path,
                approved_witness,
            )
            _require_physical_disjoint(
                origin_root,
                target,
                message="origin authority root must be physically disjoint from the restored target",
            )
        except (ArsError, OSError):
            failed.append("origin_witness_path_invalid")
    if receipt.receipt_hash != _hash_without(receipt, "receipt_hash"):
        failed.append("receipt_hash_mismatch")

    identity, identity_raw_hash = _read_json(target / "manifests" / "store-identity.json")
    actual_project = receipt.project_id
    actual_store = receipt.store_identity
    source_root: Path | None = None
    code_roots: list[str] = []
    schema_root = ""
    target_manifest_bytes_sha256 = identity_raw_hash
    expected_output_sha256 = "0" * 64
    ordinary_manifest_hash_valid = False
    if identity is None:
        failed.append("store_identity_manifest_invalid")
    else:
        recorded_hash = identity.get("manifest_hash")
        unsigned = {key: value for key, value in identity.items() if key != "manifest_hash"}
        ordinary_manifest_hash_valid = recorded_hash == sha256_hex(canonical_bytes(unsigned))
        actual_project = str(identity.get("project_id", ""))
        actual_store = str(identity.get("store_identity", ""))
        if actual_project != receipt.project_id:
            failed.append("project_identity_mismatch")
        if actual_store != receipt.store_identity:
            failed.append("store_identity_mismatch")
        roots_value = identity.get("code_roots")
        if isinstance(roots_value, list) and roots_value and all(isinstance(item, str) for item in roots_value):
            code_roots = [str(Path(item).resolve(strict=False)) for item in roots_value]
        else:
            failed.append("code_root_binding_invalid")
        if identity.get("endpoint_scheme") != receipt.source_endpoint_scheme:
            failed.append("endpoint_scheme_mismatch")
        try:
            source_root = Path(str(identity.get("control_root"))).resolve(strict=False)
        except OSError:
            failed.append("source_root_invalid")
        try:
            loaded_manifest = load_store_manifest_unbound(target)
            target_manifest_bytes_sha256 = sha256_hex((target / "manifests" / "store-identity.json").read_bytes())
            persisted_schema_root = manifest_schema_root(loaded_manifest)
            if persisted_schema_root is not None:
                schema_root = str(persisted_schema_root.resolve(strict=False))
            elif code_roots:
                schema_root = str(Path(code_roots[0]) / ".research-system" / "schemas")
        except Exception:
            failed.append("store_identity_manifest_invalid")
        else:
            if approved_witness is not None and validated_witness_path is not None:
                try:
                    immutable_preflight = _restore_preflight_anchor(
                        target,
                        loaded_manifest,
                        approved_witness,
                        validated_witness_path,
                    )
                except (ArsError, OSError, ValueError):
                    if not ordinary_manifest_hash_valid:
                        failed.append("store_identity_manifest_invalid")
                    failed.append("origin_witness_manifest_mismatch")
                else:
                    if immutable_preflight is not None:
                        source_root = Path(str(immutable_preflight["source_root"])).resolve(strict=False)
                        target_manifest_bytes_sha256 = str(immutable_preflight["target_manifest_bytes_sha256"])
                    elif not ordinary_manifest_hash_valid:
                        failed.append("store_identity_manifest_invalid")
            elif not ordinary_manifest_hash_valid:
                failed.append("store_identity_manifest_invalid")

    if source_root == target:
        failed.append("store_not_moved")

    if approved_witness is not None and validated_witness_path is not None:
        if source_root is not None and source_root != Path(approved_witness.initial_control_root):
            failed.append("origin_witness_source_mismatch")
        if origin_root is not None and source_root is not None:
            try:
                os.lstat(source_root)
            except FileNotFoundError:
                pass
            except OSError:
                failed.append("origin_witness_source_overlap")
            else:
                try:
                    _require_physical_disjoint(
                        origin_root,
                        source_root,
                        message="origin authority root must be physically disjoint from the restore source",
                    )
                except (ArsError, OSError):
                    failed.append("origin_witness_source_overlap")

    if code_roots and schema_root:
        try:
            expected_output = canonical_restore_binding_output(
                target,
                actual_project,
                actual_store,
                [Path(root) for root in code_roots],
                Path(schema_root),
            )
            expected_output_sha256 = sha256_hex(expected_output)
        except Exception:
            failed.append("restore_output_binding_invalid")

    try:
        schemas = bundled_runtime_schema_registry()
        if not code_roots:
            raise ArsError("store code roots are unavailable")
        require_existing_control_root([Path(root) for root in code_roots], target)
        ledger_snapshot = EventLedger(target, receipt.project_id, schemas).snapshot()
        resolver = LedgerAuthorityGrantResolver(
            target,
            receipt.project_id,
            receipt.store_identity,
            schemas,
            approved_witness=approved_witness,
            approved_witness_path=validated_witness_path,
            restore_source_alias=True,
        )
        replay_state = replay(
            ledger_snapshot.events,
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
        ledger_hash = sha256_hex(canonical_bytes(list(ledger_snapshot.events)))
        if (
            ledger_snapshot.global_position != receipt.canonical_tail_position
            or ledger_snapshot.event_hash != receipt.canonical_tail_hash
        ):
            failed.append("ledger_tail_mismatch")
    except Exception:
        ledger_snapshot = None
        replay_state = {}
        ledger_hash = "0" * 64
        failed.append("ledger_replay_invalid")

    snapshot, snapshot_binding = _read_bound_json(target, snapshot_path)
    snapshot_hash = snapshot_binding.raw_sha256 if snapshot_binding is not None else "0" * 64
    source_snapshot_hash = sha256_hex(canonical_bytes(snapshot)) if snapshot is not None else "0" * 64
    if snapshot is None:
        failed.append("snapshot_binding_mismatch")
    else:
        expected_snapshot = (
            snapshot_hash == receipt.snapshot_hash
            and snapshot.get("snapshot_id") == receipt.snapshot_id
            and snapshot.get("source_position") == receipt.snapshot_source_position
            and snapshot.get("source_hash") == receipt.snapshot_source_hash
            and snapshot.get("state_hash") == receipt.snapshot_state_hash
            and snapshot.get("replay_start_position") == receipt.replay_start_position
            and snapshot.get("replay_end_position") == receipt.replay_end_position
        )
        if not expected_snapshot:
            failed.append("snapshot_binding_mismatch")
        if tuple(snapshot.get("schema_versions", ())) != receipt.schema_versions:
            failed.append("schema_version_unsupported")
        if tuple(snapshot.get("tool_versions", ())) != receipt.tool_versions:
            failed.append("tool_version_unsupported")
        if snapshot.get("state_hash") != sha256_hex(canonical_bytes(replay_state)):
            failed.append("snapshot_state_mismatch")
        if ledger_snapshot is not None and (
            snapshot.get("source_position") != ledger_snapshot.global_position
            or snapshot.get("source_hash") != ledger_snapshot.event_hash
        ):
            failed.append("snapshot_tail_mismatch")

    endpoint, endpoint_binding = _read_bound_json(target, endpoint_ownership_path)
    endpoint_hash = endpoint_binding.raw_sha256 if endpoint_binding is not None else "0" * 64
    if endpoint is None or not (
        endpoint.get("target_root") == str(target)
        and endpoint.get("endpoint_scheme") == receipt.source_endpoint_scheme
        and endpoint.get("owner_actor_id") == actor_id == receipt.verified_by_actor_id
        and endpoint.get("authority_grant_id") == authority_grant_id == receipt.verification_authority_grant_id
        and endpoint.get("observed_at")
    ):
        failed.append("endpoint_authority_mismatch")

    manifest, manifest_binding = _read_bound_json(target, artefact_manifest_path)
    artefact_manifest_hash = manifest_binding.raw_sha256 if manifest_binding is not None else "0" * 64
    observations: list[dict[str, Any]] = []
    rows = manifest.get("artefacts", []) if manifest is not None else []
    bound_artefacts: list[RestoreBoundArtefact] = []
    if artefact_manifest_hash != receipt.external_artefact_manifest_hash:
        failed.append("artefact_manifest_mismatch")
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        rows = []
        failed.append("artefact_manifest_mismatch")
    rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        artefact_id = item.get("artefact_id")
        if not isinstance(artefact_id, str) or not artefact_id:
            failed.append("artefact_manifest_mismatch")
            continue
        rows_by_id.setdefault(artefact_id, []).append(item)
    if any(len(items) != 1 for items in rows_by_id.values()):
        failed.append("artefact_manifest_mismatch")
    receipt_ids = [binding.artefact_id for binding in receipt.artefact_bindings]
    if len(receipt_ids) != len(set(receipt_ids)):
        failed.append("artefact_manifest_mismatch")
    bound_paths: set[str] = set()
    bound_identities: set[tuple[int, int]] = set()
    for binding in receipt.artefact_bindings:
        matches = rows_by_id.get(binding.artefact_id, [])
        row = matches[0] if len(matches) == 1 else None
        artefact_bytes: bytes | None = None
        canonical_relative = ""
        physical_identity: tuple[int, int] | None = None
        if row is not None:
            try:
                artefact_bytes, canonical_relative, physical_identity = _read_bound_bytes(
                    target,
                    row.get("relative_path"),
                )
            except (ArsError, OSError, TypeError):
                pass
        if (
            row is None
            or row.get("artefact_hash") != binding.artefact_hash
            or row.get("availability_status") != "available"
            or row.get("authority_grant_id") != authority_grant_id
            or not row.get("observed_at")
            or artefact_bytes is None
            or physical_identity is None
            or sha256_hex(artefact_bytes) != binding.artefact_hash
            or canonical_relative in bound_paths
            or physical_identity in bound_identities
        ):
            failed.append("artefact_unavailable")
            continue
        bound_paths.add(canonical_relative)
        bound_identities.add(physical_identity)
        observation = {
            "artefact_id": row["artefact_id"],
            "artefact_hash": row["artefact_hash"],
            "availability_status": row["availability_status"],
            "observed_at": row["observed_at"],
            "authority_grant_id": row["authority_grant_id"],
        }
        observations.append(observation)
        bound_artefacts.append(
            RestoreBoundArtefact(
                artefact_id=binding.artefact_id,
                relative_path=canonical_relative,
                artefact_sha256=binding.artefact_hash,
                observation_sha256=sha256_hex(canonical_bytes(observation)),
            )
        )
    availability_hash = sha256_hex(canonical_bytes(observations))
    if receipt.availability_status != "available" or availability_hash != receipt.availability_observation_hash:
        failed.append("availability_observation_mismatch")

    registry_hash = str(getattr(registry, "registry_hash", ""))
    try:
        registry_state_sha256 = _registry_state_sha256(registry)
    except ArsError:
        registry_state_sha256 = "0" * 64
        failed.append("registered_topology_incomplete")
    if registry_hash != receipt.evidence_registry_hash:
        failed.append("registry_hash_mismatch")
    try:
        checked = set(registry.checked_locations())
    except (AttributeError, ValueError):
        checked = set()
        failed.append("registered_topology_incomplete")
    if target not in checked or source_root is None or source_root not in checked:
        failed.append("registered_topology_incomplete")
    if actor_id != receipt.verified_by_actor_id or (
        actor_id,
        authority_grant_id,
    ) not in getattr(registry, "verifier_authority_bindings", ()):
        failed.append("verification_authority_mismatch")

    predicates = tuple(sorted(set(failed)))
    result = RestorePreflightResult(
        status="diagnostic_only" if predicates else "verified",
        failed_predicates=predicates,
        receipt_hash=receipt.receipt_hash,
        ledger_hash=ledger_hash,
        snapshot_hash=snapshot_hash,
        target_endpoint_ownership_hash=endpoint_hash,
        artefact_manifest_hash=artefact_manifest_hash,
        availability_observations_hash=availability_hash,
        registry_hash=registry_hash,
        target_root=str(target),
        project_id=actual_project,
        store_identity=actual_store,
        tail_position=(ledger_snapshot.global_position if ledger_snapshot else -1),
        tail_hash=(ledger_snapshot.event_hash if ledger_snapshot else "0" * 64),
        snapshot_id=str(snapshot.get("snapshot_id", "")) if snapshot else "",
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
        result_hash="",
        source_root=str(source_root) if source_root is not None else "",
        code_roots=code_roots,
        schema_root=schema_root,
        source_snapshot_hash=source_snapshot_hash,
        target_manifest_bytes_sha256=target_manifest_bytes_sha256,
        expected_output_sha256=expected_output_sha256,
        origin_witness_path=(str(validated_witness_path) if validated_witness_path is not None else ""),
        origin_witness_sha256=approved_witness.raw_sha256 if approved_witness is not None else "",
        origin_initial_control_root=(approved_witness.initial_control_root if approved_witness is not None else ""),
        origin_initial_physical_root_identity=(
            dict(approved_witness.initial_physical_root_identity) if approved_witness is not None else {}
        ),
    )
    sealed = seal_restore_preflight_result(result)
    closure = None
    if (
        sealed.status == "verified"
        and snapshot_binding is not None
        and endpoint_binding is not None
        and manifest_binding is not None
        and len(bound_artefacts) == len(receipt.artefact_bindings)
    ):
        closure = RestoreAdmissionClosure(
            target_root=str(target),
            snapshot=snapshot_binding,
            endpoint_ownership=endpoint_binding,
            artefact_manifest=manifest_binding,
            artefacts=tuple(bound_artefacts),
            registry=registry,
            registry_state_sha256=registry_state_sha256,
        )
    carried = _RestorePreflightWithClosure(**asdict(sealed))
    object.__setattr__(carried, "_admission_closure", closure)
    bundle = RestoreAdmissionBundle(result=carried, closure=closure)
    return bundle if _capture_bundle else carried


def prepare_restore_admission_before_writer_lease(
    *,
    target_root: Path,
    receipt: BackupReceipt,
    snapshot_path: Path,
    endpoint_ownership_path: Path,
    artefact_manifest_path: Path,
    registry: object,
    actor_id: str,
    authority_grant_id: str,
    approved_witness: StoreOriginWitness | None = None,
    approved_witness_path: Path | None = None,
) -> RestoreAdmissionBundle:
    """Run the full preflight once and retain its exact bounded input closure."""
    bundle = verify_restore_before_writer_lease(
        target_root=target_root,
        receipt=receipt,
        snapshot_path=snapshot_path,
        endpoint_ownership_path=endpoint_ownership_path,
        artefact_manifest_path=artefact_manifest_path,
        registry=registry,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
        approved_witness=approved_witness,
        approved_witness_path=approved_witness_path,
        _capture_bundle=True,
    )
    if not isinstance(bundle, RestoreAdmissionBundle):
        raise ArsError("restore admission preparation did not return a checked-input bundle")
    return bundle


def revalidate_restore_admission_closure(bundle: RestoreAdmissionBundle) -> None:
    """Recheck the full preflight's bounded mutable inputs under the target lock."""
    closure = bundle.closure
    if closure is None:
        raise ArsError("verified restore admission requires checked-input closure")
    target = Path(closure.target_root)
    for label, expected in (
        ("snapshot", closure.snapshot),
        ("endpoint ownership", closure.endpoint_ownership),
        ("artefact manifest", closure.artefact_manifest),
    ):
        value, observed = _read_bound_json(target, target / Path(expected.relative_path))
        if (
            value is None
            or observed is None
            or observed.raw_sha256 != expected.raw_sha256
            or observed.canonical_sha256 != expected.canonical_sha256
        ):
            raise IntegrityError(f"restore {label} changed after full preflight")
    for expected in closure.artefacts:
        try:
            data, relative, _identity = _read_bound_bytes(target, expected.relative_path)
        except (ArsError, OSError) as exc:
            raise IntegrityError("restore artefact changed after full preflight") from exc
        if relative != expected.relative_path or sha256_hex(data) != expected.artefact_sha256:
            raise IntegrityError("restore artefact changed after full preflight")
    try:
        current_registry_sha256 = _registry_state_sha256(closure.registry)
    except ArsError as exc:
        raise IntegrityError("restore registry changed after full preflight") from exc
    if current_registry_sha256 != closure.registry_state_sha256:
        raise IntegrityError("restore registry changed after full preflight")


def seal_restore_preflight_result(
    result: RestorePreflightResult,
) -> RestorePreflightResult:
    """Return the result with its canonical content hash populated."""
    return replace(result, result_hash=_hash_without(result, "result_hash"))


def validate_restore_preflight_result(
    result: RestorePreflightResult,
    *,
    current_root: Path,
    project_id: str,
    actor_id: str,
    authority_grant_id: str,
    approved_witness: StoreOriginWitness | None = None,
) -> None:
    """Recheck a preflight result immediately before writer-lock acquisition."""
    if not isinstance(result, RestorePreflightResult):
        raise ArsError("restore preflight result required")
    if result.result_hash != _hash_without(result, "result_hash"):
        raise ArsError("restore preflight result hash mismatch")
    if result.status != "verified" or result.failed_predicates:
        raise ArsError("restore preflight is not verified")
    if Path(result.target_root).resolve(strict=False) != current_root.resolve(strict=False):
        raise ArsError("restore preflight target root mismatch")
    if result.project_id != project_id:
        raise ArsError("restore preflight project mismatch")
    if result.actor_id != actor_id or result.authority_grant_id != authority_grant_id:
        raise ArsError("restore preflight authority mismatch")
    if approved_witness is None:
        raise ArsError("restore preflight requires approved origin witness")
    if (
        result.origin_witness_sha256 != approved_witness.raw_sha256
        or result.origin_initial_control_root != approved_witness.initial_control_root
        or result.origin_initial_physical_root_identity != approved_witness.initial_physical_root_identity
    ):
        raise ArsError("restore preflight origin witness mismatch")
