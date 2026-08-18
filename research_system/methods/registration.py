"""Durable candidate registration for owner-operated methods documents."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import stat
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConfigurationError, ConflictError, IntegrityError
from research_system.git_execution import run_git
from research_system.store.contained_files import (
    publish_contained_exact_no_replace,
    read_contained_file,
    remove_contained_exact,
    validate_contained_destination,
)


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


@dataclass(frozen=True)
class PreparedRawRegistration:
    """Fully validated raw publication material with no durable side effect."""

    registration: CandidateRegistration
    publication: RawContentPublication
    raw_bytes: bytes
    command: dict[str, Any]


@dataclass(frozen=True)
class PreparedCandidateRegistration:
    value: dict[str, Any]
    registration: CandidateRegistration
    raw_bytes: bytes
    content_sha256: str
    relative_path: str
    command: dict[str, Any]


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

    def _write(self, artefact_id: str, raw_bytes: bytes) -> str:
        relative = Path(self.relative_path(artefact_id))
        publish_contained_exact_no_replace(
            self.control_root,
            relative.as_posix(),
            raw_bytes,
            conflict_message="methods document identity already binds different bytes",
        )
        return relative.as_posix()

    def write(self, artefact_id: str, raw_bytes: bytes) -> str:
        """Publish candidate document bytes through the historical public seam."""

        return self._write(artefact_id, raw_bytes)

    def publish_bytes(self, artefact_id: str, raw_bytes: bytes) -> str:
        """Publish non-artefact coordinator bytes without resembling an ObjectStore kind call."""

        return self._write(artefact_id, raw_bytes)


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
_REGISTRATION_RECOVERY_DIRECTORY = Path("runtime/registered-content-recovery")
_REGISTRATION_RECOVERY_SCHEMA_ID = "ars://internal/registered-content-recovery"


def spec_brief_input_artefact_id(source_relative_path: str, content_sha256: str) -> str:
    """Derive the sole artefact identity for one exact governed brief input."""

    path = Path(source_relative_path)
    posix = path.as_posix()
    allowed = posix in _SPEC_SOURCE_PATHS or (
        posix.startswith(_METHODS_ASSET_PREFIX)
        and path.parent.as_posix() == _METHODS_ASSET_PREFIX.rstrip("/")
        and path.suffix == ".md"
    )
    if (
        path.is_absolute()
        or ".." in path.parts
        or posix != source_relative_path
        or not allowed
        or not isinstance(content_sha256, str)
        or len(content_sha256) != 64
        or any(character not in "0123456789abcdef" for character in content_sha256)
    ):
        raise ConfigurationError("SPEC brief input identity is invalid")
    digest = bytearray(
        hashlib.sha256(
            canonical_bytes(
                {
                    "kind": "spec-brief-input",
                    "source_relative_path": source_relative_path,
                    "content_sha256": content_sha256,
                }
            )
        ).digest()[:16]
    )
    digest[6] = (digest[6] & 0x0F) | 0x70
    digest[8] = (digest[8] & 0x3F) | 0x80
    return f"art_{uuid.UUID(bytes=bytes(digest))}"


def _git(repository_root: Path, *arguments: str) -> str:
    result = run_git(
        repository_root,
        *arguments,
        unavailable_message="raw content Git binding is unavailable",
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
    expected_document_type = "spec_operator_source" if posix in _SPEC_SOURCE_PATHS else "methods_asset"
    if publication.document_type != expected_document_type:
        raise ConfigurationError("raw content document type does not match its source path")
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
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ConfigurationError("raw content source is unavailable") from exc
    committed_blob = _git(root, "rev-parse", f"HEAD:{posix}")
    working_result = run_git(
        root,
        "hash-object",
        "--path",
        posix,
        "--stdin",
        input=raw,
        text=False,
        unavailable_message="raw content Git binding is unavailable",
    )
    if working_result.returncode != 0:
        raise ConfigurationError("raw content Git binding is unavailable")
    try:
        working_blob = working_result.stdout.decode("ascii").strip()
    except (AttributeError, UnicodeError) as exc:
        raise ConfigurationError("raw content Git binding returned invalid output") from exc
    if committed_blob != publication.source_git_blob or working_blob != committed_blob:
        raise ConfigurationError("raw content source is not the exact committed Git blob")
    if len(raw) != publication.size_bytes or sha256_hex(raw) != publication.content_sha256:
        raise ConfigurationError("raw content byte binding differs")
    return raw


def _write_immutable_raw(control_root: Path, relative_path: str, raw: bytes) -> None:
    publish_contained_exact_no_replace(
        control_root,
        relative_path,
        raw,
        conflict_message="raw content destination already binds different bytes",
    )


def _registration_event_matches(event: object, command: dict[str, Any]) -> bool:
    return bool(
        isinstance(event, dict)
        and event.get("event_type") == "ArtefactRegistered"
        and all(
            event.get(key) == command.get(key)
            for key in (
                "command_id",
                "command_type",
                "actor_id",
                "authority_grant_id",
                "idempotency_key",
                "correlation_id",
                "causation_id",
                "project_id",
            )
        )
        and event.get("stream_id") == command.get("target_stream_id")
        and event.get("command_payload_hash") == sha256_hex(canonical_bytes(command.get("payload")))
        and event.get("payload") == command.get("payload")
    )


def _recovery_marker(command: dict[str, Any], relative_path: str, raw: bytes) -> dict[str, Any]:
    return {
        "schema_id": _REGISTRATION_RECOVERY_SCHEMA_ID,
        "schema_version": "1.0.0",
        "command": command,
        "relative_path": relative_path,
        "raw_base64": base64.b64encode(raw).decode("ascii"),
        "raw_sha256": sha256_hex(raw),
        "size_bytes": len(raw),
    }


def _recovery_marker_bytes(command: dict[str, Any], relative_path: str, raw: bytes) -> bytes:
    return canonical_bytes(_recovery_marker(command, relative_path, raw))


def _publish_recovery_marker(control_root: Path, command: dict[str, Any], relative_path: str, raw: bytes) -> str:
    store = CandidateDocumentStore(control_root, relative_directory=_REGISTRATION_RECOVERY_DIRECTORY)
    return store.publish_bytes(str(command["command_id"]), _recovery_marker_bytes(command, relative_path, raw))


def _after_registered_bytes_published(_control_root: Path, _relative_path: str, _raw: bytes) -> None:
    """Test seam after marker-bound bytes are durable but before command admission."""


def _require_exact_registered_bytes(control_root: Path, relative_path: str, raw: bytes) -> None:
    """Fail closed if command acceptance is not still bound to exact final bytes."""

    try:
        actual = read_contained_file(control_root, relative_path)
    except FileNotFoundError as exc:
        raise IntegrityError("registered content is absent after command acceptance") from exc
    if actual != raw:
        raise IntegrityError("registered content differs after command acceptance")


def _remove_recovery_marker(
    control_root: Path,
    command: dict[str, Any],
    relative_path: str,
    raw: bytes,
) -> None:
    marker_relative = (_REGISTRATION_RECOVERY_DIRECTORY / f"{command['command_id']}.json").as_posix()
    remove_contained_exact(
        control_root,
        marker_relative,
        expected=_recovery_marker_bytes(command, relative_path, raw),
        conflict_message="registration recovery marker changed before completion",
    )


def _is_abandoned_recovery_staging_file(path: Path) -> bool:
    """Recognize non-authoritative staging leaves left by a hard process stop."""

    name = path.name
    if not name.startswith(".") or not name.endswith(".tmp"):
        return False
    marker_name, separator, nonce = name[1:-4].rpartition(".")
    if not separator or not marker_name.endswith(".json") or len(nonce) != 32:
        return False
    return all(character in "0123456789abcdef" for character in nonce)


def recover_registered_content(control_root: Path, events: tuple[dict[str, Any], ...]) -> None:
    """Reconcile committed registrations with their exact pre-submit byte markers."""

    root = control_root.resolve(strict=True)
    directory = root / _REGISTRATION_RECOVERY_DIRECTORY
    try:
        metadata = directory.lstat()
    except FileNotFoundError:
        return
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    ):
        raise ConfigurationError("registration recovery directory is not physical")
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if _is_abandoned_recovery_staging_file(path):
            metadata = path.lstat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            ):
                raise IntegrityError("registration recovery directory contains an invalid staging entry")
            continue
        if path.suffix != ".json" or not path.is_file() or path.is_symlink():
            raise IntegrityError("registration recovery directory contains an invalid entry")
        relative_marker = path.relative_to(root).as_posix()
        raw_marker = read_contained_file(root, relative_marker)
        try:
            marker = json.loads(raw_marker)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("registration recovery marker is invalid") from exc
        if (
            not isinstance(marker, dict)
            or raw_marker != canonical_bytes(marker)
            or set(marker)
            != {
                "schema_id",
                "schema_version",
                "command",
                "relative_path",
                "raw_base64",
                "raw_sha256",
                "size_bytes",
            }
            or marker.get("schema_id") != _REGISTRATION_RECOVERY_SCHEMA_ID
            or marker.get("schema_version") != "1.0.0"
        ):
            raise IntegrityError("registration recovery marker is invalid")
        command = marker.get("command")
        relative_path = marker.get("relative_path")
        try:
            raw = base64.b64decode(marker.get("raw_base64"), validate=True)
        except (binascii.Error, TypeError, ValueError) as exc:
            raise IntegrityError("registration recovery marker bytes are invalid") from exc
        payload = command.get("payload") if isinstance(command, dict) else None
        manifest = payload.get("manifest") if isinstance(payload, dict) else None
        artefact_id = command.get("target_stream_id") if isinstance(command, dict) else None
        if (
            not isinstance(relative_path, str)
            or not isinstance(manifest, dict)
            or not isinstance(artefact_id, str)
            or path.name != f"{command.get('command_id')}.json"
            or payload.get("new_artefact_id") != artefact_id
            or manifest.get("artefact_id") != artefact_id
            or manifest.get("relative_path") != relative_path
            or Path(relative_path).stem != artefact_id
            or manifest.get("content_sha256") != marker.get("raw_sha256")
            or manifest.get("size_bytes") != marker.get("size_bytes")
            or len(raw) != marker.get("size_bytes")
            or sha256_hex(raw) != marker.get("raw_sha256")
        ):
            raise IntegrityError("registration recovery marker binding differs")
        matches = [event for event in events if _registration_event_matches(event, command)]
        competing = [
            event
            for event in events
            if event.get("event_type") == "ArtefactRegistered" and event.get("stream_id") == artefact_id
        ]
        if len(matches) > 1 or (not matches and competing):
            raise IntegrityError("registration recovery event binding differs")
        if not matches:
            continue
        _write_immutable_raw(root, relative_path, raw)
        _remove_recovery_marker(root, command, relative_path, raw)


def publish_registered_raw_content(
    *,
    repository_root: Path,
    publication: RawContentPublication,
    registration: CandidateRegistration,
    control_root: Path,
    command_service: CommandSubmitter,
) -> RegisteredCandidate:
    """Publish marker-bound raw bytes before admitting their immutable registration.

    The exact recovery marker is the durable provisional binding.  This order
    prevents an accepted registration from ever depending on a later mutable
    pathname operation.  A crash before command admission leaves marker plus
    exact bytes; an exact retry reuses that marker and command identity.
    Explicit command rejection removes the marker but safely leaves the exact,
    unregistered immutable bytes because their ownership cannot be inferred
    from a no-replace publication race.
    """

    prepared = prepare_registered_raw_content(
        repository_root=repository_root,
        publication=publication,
        registration=registration,
        control_root=control_root,
    )
    raw = prepared.raw_bytes
    command = prepared.command
    _publish_recovery_marker(control_root, command, publication.destination_relative_path, raw)
    try:
        _write_immutable_raw(control_root, publication.destination_relative_path, raw)
    except ConflictError:
        _remove_recovery_marker(control_root, command, publication.destination_relative_path, raw)
        raise
    _after_registered_bytes_published(control_root, publication.destination_relative_path, raw)
    receipt = command_service.submit(command)
    if getattr(receipt, "status", None) not in {"accepted", "replayed"}:
        _remove_recovery_marker(control_root, command, publication.destination_relative_path, raw)
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        raise ArsError(f"raw artefact registration was not accepted ({reason})")
    _require_exact_registered_bytes(control_root, publication.destination_relative_path, raw)
    _remove_recovery_marker(control_root, command, publication.destination_relative_path, raw)
    return RegisteredCandidate(
        registration.artefact_id,
        publication.content_sha256,
        raw,
        publication.destination_relative_path,
        receipt,
    )


def prepare_registered_raw_content(
    *,
    repository_root: Path,
    publication: RawContentPublication,
    registration: CandidateRegistration,
    control_root: Path,
) -> PreparedRawRegistration:
    """Validate and derive one raw-content registration without publishing it."""

    raw = _validate_committed_raw_source(repository_root, publication)
    destination = Path(publication.destination_relative_path)
    expected_artefact_id = spec_brief_input_artefact_id(
        publication.source_relative_path,
        publication.content_sha256,
    )
    expected_destination = f"{_RAW_DESTINATION_PREFIX}{expected_artefact_id}.md"
    if (
        registration.artefact_id != expected_artefact_id
        or destination.stem != expected_artefact_id
        or publication.destination_relative_path != expected_destination
    ):
        raise ConfigurationError("raw content destination does not bind the artefact identity")
    validate_contained_destination(control_root, publication.destination_relative_path)
    try:
        existing = read_contained_file(control_root, publication.destination_relative_path)
    except FileNotFoundError:
        existing = None
    if existing is not None and existing != raw:
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
    return PreparedRawRegistration(registration, publication, raw, command)


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
    """Publish marker-bound candidate bytes before immutable command admission.

    The marker and exact no-replace final leaf form one recoverable provisional
    state.  Command submission therefore never accepts an artefact whose bytes
    still need a later pathname mutation.  Exact retries after a pre-submit or
    response interruption reuse the same bytes and command identity.  An
    explicit rejection removes only the marker and leaves exact unregistered
    bytes rather than risking deletion of an equal competing publication.
    """
    prepared = prepare_candidate_document(
        value=value,
        registration=registration,
        document_store=document_store,
    )
    try:
        existing = read_contained_file(document_store.control_root, prepared.relative_path)
    except FileNotFoundError:
        existing = None
    if existing is not None and existing != prepared.raw_bytes:
        raise ConflictError("methods document identity already binds different bytes")
    _publish_recovery_marker(
        document_store.control_root,
        prepared.command,
        prepared.relative_path,
        prepared.raw_bytes,
    )
    try:
        document_store.write(registration.artefact_id, prepared.raw_bytes)
    except ConflictError:
        _remove_recovery_marker(
            document_store.control_root,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )
        raise
    _after_registered_bytes_published(document_store.control_root, prepared.relative_path, prepared.raw_bytes)
    receipt = command_service.submit(prepared.command)
    if getattr(receipt, "status", None) not in {"accepted", "replayed"}:
        _remove_recovery_marker(
            document_store.control_root,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        explanation = getattr(receipt, "explanation", None)
        detail = f": {explanation}" if explanation else ""
        raise ArsError(f"candidate artefact registration was not accepted ({reason}){detail}")
    _require_exact_registered_bytes(document_store.control_root, prepared.relative_path, prepared.raw_bytes)
    _remove_recovery_marker(
        document_store.control_root,
        prepared.command,
        prepared.relative_path,
        prepared.raw_bytes,
    )
    return RegisteredCandidate(
        registration.artefact_id,
        prepared.content_sha256,
        prepared.raw_bytes,
        prepared.relative_path,
        receipt,
    )


def prepare_candidate_document(
    *,
    value: dict[str, Any],
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
) -> PreparedCandidateRegistration:
    """Derive one candidate-document registration without publishing it."""

    raw = canonical_bytes(value)
    digest = sha256_hex(raw)
    relative_path = document_store.relative_path(registration.artefact_id)
    validate_contained_destination(document_store.control_root, relative_path)
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
    return PreparedCandidateRegistration(value, registration, raw, digest, relative_path, command)


__all__ = [
    "CandidateDocumentStore",
    "CandidateRegistration",
    "PreparedRawRegistration",
    "PreparedCandidateRegistration",
    "CommandSubmitter",
    "RawContentPublication",
    "RegisteredCandidate",
    "publish_registered_raw_content",
    "prepare_registered_raw_content",
    "prepare_candidate_document",
    "recover_registered_content",
    "register_candidate_document",
    "spec_brief_input_artefact_id",
]
