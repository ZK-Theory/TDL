"""Durable candidate registration for owner-operated methods documents."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConfigurationError, ConflictError
from research_system.store.durability import fsync_directory


class CommandSubmitter(Protocol):
    def submit(self, envelope: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class CandidateRegistration:
    """Caller-authorized production metadata for one immutable document."""

    artefact_id: str
    project_id: str
    actor_id: str
    authority_grant_id: str
    submitted_at: str
    correlation_id: str
    reason: str
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RegisteredCandidate:
    artefact_id: str
    content_sha256: str
    raw_bytes: bytes
    relative_path: str
    receipt: Any


class CandidateDocumentStore:
    """Write exact canonical bytes once beneath the configured control root."""

    def __init__(
        self,
        control_root: Path,
        *,
        root_id: str = "control",
        relative_directory: Path = Path("methods/documents"),
    ) -> None:
        self.control_root = control_root.resolve(strict=True)
        self.root_id = root_id
        if relative_directory.is_absolute() or ".." in relative_directory.parts:
            raise ValueError("candidate document directory must be control-relative")
        self.relative_directory = relative_directory

    def relative_path(self, artefact_id: str) -> str:
        """Return the final control-relative path without publishing bytes."""
        return (self.relative_directory / f"{artefact_id}.json").as_posix()

    def write(self, artefact_id: str, raw_bytes: bytes) -> str:
        relative = Path(self.relative_path(artefact_id))
        target = self.control_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if target.read_bytes() != raw_bytes:
                raise ConflictError("methods document identity already binds different bytes")
            return relative.as_posix()
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        fsync_directory(target.parent)
        return relative.as_posix()


@dataclass(frozen=True)
class RawContentPublication:
    """Exact committed raw content admitted to the owner-operated brief seam."""

    source_relative_path: str
    source_git_blob: str
    content_sha256: str
    size_bytes: int
    media_type: str
    document_type: str
    destination_relative_path: str


_SPEC_SOURCE_PATHS = frozenset(
    {
        ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
        ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
    }
)
_METHODS_ASSET_PREFIX = ".research-system/methods/assets/"
_RAW_DESTINATION_PREFIX = "methods/content/spec-flow/"


def _require_physical_destination(control_root: Path, relative_path: str, *, create: bool = False) -> Path:
    root = control_root.resolve(strict=True)
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != relative_path:
        raise ConfigurationError("raw content destination is not canonical and control-relative")
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
                raise ConfigurationError("raw content destination parent is unavailable") from exc
        except OSError as exc:
            raise ConfigurationError("raw content destination parent is unavailable") from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & reparse
        ):
            raise ConfigurationError("raw content destination parent is not a physical directory")
    target = current / relative.name
    if not missing_parent and (target.exists() or target.is_symlink()):
        try:
            metadata = target.lstat()
        except OSError as exc:
            raise ConfigurationError("raw content destination is unavailable") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or getattr(metadata, "st_file_attributes", 0) & reparse
        ):
            raise ConfigurationError("raw content destination is not a physical regular file")
    return target


def _git(repository_root: Path, *arguments: str) -> str:
    result = subprocess.run(  # nosec B603 B607 - fixed Git executable and arguments
        ["git", "-C", str(repository_root), *arguments],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise ConfigurationError("raw content Git binding is unavailable")
    return result.stdout.strip()


def _validate_committed_raw_source(repository_root: Path, publication: RawContentPublication) -> bytes:
    root = repository_root.resolve(strict=True)
    if Path(_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True) != root:
        raise ConfigurationError("raw content repository is not the configured Git worktree root")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise ConfigurationError("raw content repository is not clean")
    relative = Path(publication.source_relative_path)
    posix = relative.as_posix()
    allowed = posix in _SPEC_SOURCE_PATHS or (
        posix.startswith(_METHODS_ASSET_PREFIX)
        and relative.parent.as_posix() == _METHODS_ASSET_PREFIX.rstrip("/")
        and relative.suffix == ".md"
    )
    if relative.is_absolute() or ".." in relative.parts or not allowed or "scale" in posix.casefold():
        raise ConfigurationError("raw content source is outside the SPEC brief allowlist")
    if publication.document_type not in {"spec_operator_source", "methods_asset"}:
        raise ConfigurationError("raw content document type is unsupported")
    if publication.media_type != "text/markdown; charset=utf-8":
        raise ConfigurationError("raw content media type is unsupported")
    destination = Path(publication.destination_relative_path)
    destination_posix = destination.as_posix()
    if (
        destination.is_absolute()
        or ".." in destination.parts
        or not destination_posix.startswith(_RAW_DESTINATION_PREFIX)
        or destination.suffix != ".md"
    ):
        raise ConfigurationError("raw content destination is outside the SPEC content root")
    source = (root / relative).resolve(strict=True)
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ConfigurationError("raw content source escapes the repository") from exc
    raw = source.read_bytes()
    committed_blob = _git(root, "rev-parse", f"HEAD:{posix}")
    working_blob = _git(root, "hash-object", "--", posix)
    if committed_blob != publication.source_git_blob or working_blob != committed_blob:
        raise ConfigurationError("raw content source is not the exact committed Git blob")
    if len(raw) != publication.size_bytes or sha256_hex(raw) != publication.content_sha256:
        raise ConfigurationError("raw content byte binding differs")
    return raw


def _write_immutable_raw(control_root: Path, relative_path: str, raw: bytes) -> None:
    target = _require_physical_destination(control_root, relative_path, create=True)
    try:
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileExistsError:
        target = _require_physical_destination(control_root, relative_path)
        if target.read_bytes() != raw:
            raise ConflictError("raw content destination already binds different bytes")
        return
    with os.fdopen(fd, "wb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ConfigurationError("raw content destination is not a physical regular file")
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(target.parent)


def publish_registered_raw_content(
    *,
    repository_root: Path,
    publication: RawContentPublication,
    registration: CandidateRegistration,
    control_root: Path,
    command_service: CommandSubmitter,
) -> RegisteredCandidate:
    """Register then immutably publish one exact committed SPEC/methods markdown file.

    Registration precedes byte publication so an interruption cannot leave an
    unregistered file.  Exact retry replays the command and reconciles the
    missing immutable bytes, matching candidate-document recovery semantics.
    """

    raw = _validate_committed_raw_source(repository_root, publication)
    destination = Path(publication.destination_relative_path)
    if destination.stem != registration.artefact_id:
        raise ConfigurationError("raw content destination does not bind the artefact identity")
    target = _require_physical_destination(control_root, publication.destination_relative_path)
    if target.exists() and target.read_bytes() != raw:
        raise ConflictError("raw content destination already binds different bytes")
    manifest = deepcopy(registration.manifest)
    if manifest.get("artefact_id") != registration.artefact_id:
        raise ArsError("registration manifest does not bind the raw artefact")
    manifest.update(
        {
            "root_id": "control",
            "relative_path": publication.destination_relative_path,
            "size_bytes": publication.size_bytes,
            "media_type": publication.media_type,
            "content_sha256": publication.content_sha256,
            "artefact_type": publication.document_type,
        }
    )
    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise ArsError("registration manifest authority is missing")
    authority["use_authority"] = "candidate"
    metadata_digest = sha256_hex(canonical_bytes(manifest))
    idempotency_key = f"methods-register-raw:{registration.artefact_id}:{metadata_digest}"
    command = {
        "command_id": _stable_command_id(idempotency_key),
        "command_type": "RegisterArtefact",
        "schema_id": "ars://core/command/RegisterArtefact",
        "schema_version": "1.0.0",
        "submitted_at": registration.submitted_at,
        "actor_id": registration.actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": registration.authority_grant_id,
        "target_stream_id": registration.artefact_id,
        "expected_stream_version": 0,
        "idempotency_key": idempotency_key,
        "correlation_id": registration.correlation_id,
        "causation_id": None,
        "reason": registration.reason,
        "evidence_refs": [],
        "payload": {"new_artefact_id": registration.artefact_id, "manifest": manifest},
        "project_id": registration.project_id,
    }
    receipt = command_service.submit(command)
    if getattr(receipt, "status", None) not in {"accepted", "replayed"}:
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        raise ArsError(f"raw artefact registration was not accepted ({reason})")
    _write_immutable_raw(control_root, publication.destination_relative_path, raw)
    return RegisteredCandidate(
        registration.artefact_id,
        publication.content_sha256,
        raw,
        publication.destination_relative_path,
        receipt,
    )


def _stable_command_id(idempotency_key: str) -> str:
    """Derive one canonical UUIDv7 command identity for an exact registration."""
    value = int.from_bytes(hashlib.sha256(idempotency_key.encode("utf-8")).digest()[:16], "big")
    value = (value & ~(0xF << 76)) | (0x7 << 76)
    value = (value & ~(0b11 << 62)) | (0b10 << 62)
    return f"cmd_{uuid.UUID(int=value)}"


def register_candidate_document(
    *,
    value: dict[str, Any],
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
    command_service: CommandSubmitter,
) -> RegisteredCandidate:
    """Persist and register exact bytes, always forcing initial candidate authority."""
    raw = canonical_bytes(value)
    digest = sha256_hex(raw)
    relative_path = document_store.relative_path(registration.artefact_id)
    manifest = deepcopy(registration.manifest)
    if manifest.get("artefact_id") != registration.artefact_id:
        raise ArsError("registration manifest does not bind the document artefact")
    manifest.update(
        {
            "root_id": document_store.root_id,
            "relative_path": relative_path,
            "size_bytes": len(raw),
            "media_type": "application/json",
            "content_sha256": digest,
        }
    )
    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise ArsError("registration manifest authority is missing")
    authority["use_authority"] = "candidate"
    idempotency_key = f"methods-register:{registration.artefact_id}:{digest}"
    command = {
        "command_id": _stable_command_id(idempotency_key),
        "command_type": "RegisterArtefact",
        "schema_id": "ars://core/command/RegisterArtefact",
        "schema_version": "1.0.0",
        "submitted_at": registration.submitted_at,
        "actor_id": registration.actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": registration.authority_grant_id,
        "target_stream_id": registration.artefact_id,
        "expected_stream_version": 0,
        "idempotency_key": idempotency_key,
        "correlation_id": registration.correlation_id,
        "causation_id": None,
        "reason": registration.reason,
        "evidence_refs": [],
        "payload": {"new_artefact_id": registration.artefact_id, "manifest": manifest},
        "project_id": registration.project_id,
    }
    receipt = command_service.submit(command)
    if getattr(receipt, "status", None) not in {"accepted", "replayed"}:
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        explanation = getattr(receipt, "explanation", None)
        detail = f": {explanation}" if explanation else ""
        raise ArsError(f"candidate artefact registration was not accepted ({reason}){detail}")
    document_store.write(registration.artefact_id, raw)
    return RegisteredCandidate(registration.artefact_id, digest, raw, relative_path, receipt)


__all__ = [
    "CandidateDocumentStore",
    "CandidateRegistration",
    "CommandSubmitter",
    "RawContentPublication",
    "RegisteredCandidate",
    "publish_registered_raw_content",
    "register_candidate_document",
]
