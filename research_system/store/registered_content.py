"""Physically anchored storage and recovery for registered immutable content."""

from __future__ import annotations

import base64
import json
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.errors import ConfigurationError, IntegrityError
from research_system.store.lock import DirectoryAnchor, LockedRoot, open_registered_root_anchor


class CandidateDocumentStore:
    """Write exact bytes through physically anchored in-root directories."""

    def __init__(
        self,
        control_root: Path,
        *,
        root_id: str = "control",
        relative_directory: Path = Path("methods/documents"),
        recovery_directory: Path = Path("runtime/registered-content-recovery"),
    ) -> None:
        self.control_root = control_root.resolve(strict=True)
        self.root_id = root_id
        self.relative_directory = self._require_relative_directory(relative_directory)
        self.recovery_directory = self._require_relative_directory(recovery_directory)

    @staticmethod
    def _require_relative_directory(value: Path) -> Path:
        if (
            value.is_absolute()
            or not value.parts
            or any(part in {"", ".", ".."} for part in value.parts)
            or value.as_posix() != str(value).replace("\\", "/")
        ):
            raise ValueError("candidate document directory must be canonical and control-relative")
        return value

    @staticmethod
    def _relative_file(value: str) -> Path:
        path = Path(value)
        if (
            path.is_absolute()
            or len(path.parts) < 2
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.as_posix() != value
        ):
            raise ConfigurationError("registered content path must be canonical and control-relative")
        return path

    @contextmanager
    def _open_directory(
        self,
        relative: Path,
        *,
        create: bool,
        root_anchor: DirectoryAnchor | LockedRoot | None = None,
    ) -> Iterator[DirectoryAnchor]:
        """Open one anchored member directory without masking caller failure."""

        anchors: list[DirectoryAnchor] = []
        primary_error: BaseException | None = None
        try:
            current = root_anchor
            if current is None:
                current = open_registered_root_anchor(self.control_root, delete_protect=True)
                anchors.append(current)
            for part in relative.parts:
                current = current.open_member_directory(part, create=create)
                anchors.append(current)
            yield current
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            cleanup_error: BaseException | None = None
            for anchor in reversed(anchors):
                try:
                    anchor.close()
                except BaseException as exc:
                    if cleanup_error is None:
                        cleanup_error = exc
            if cleanup_error is not None:
                if primary_error is not None:
                    raise primary_error.with_traceback(primary_error.__traceback__) from cleanup_error
                raise cleanup_error

    def relative_path(self, artefact_id: str) -> str:
        """Return the final control-relative path without publishing bytes."""

        return (self.relative_directory / f"{artefact_id}.json").as_posix()

    def write(self, artefact_id: str, raw_bytes: bytes) -> str:
        relative_path = self.relative_path(artefact_id)
        self.write_relative(relative_path, raw_bytes)
        return relative_path

    def write_relative(
        self,
        relative_path: str,
        raw_bytes: bytes,
        *,
        root_anchor: DirectoryAnchor | LockedRoot | None = None,
    ) -> None:
        relative = self._relative_file(relative_path)
        with self._open_directory(relative.parent, create=True, root_anchor=root_anchor) as directory:
            directory.write_exact_file(relative.name, raw_bytes)

    def read_relative(
        self,
        relative_path: str,
        *,
        root_anchor: DirectoryAnchor | LockedRoot | None = None,
    ) -> bytes:
        relative = self._relative_file(relative_path)
        with self._open_directory(relative.parent, create=False, root_anchor=root_anchor) as directory:
            return directory.read_regular_file(relative.name)

    def publish_registered(
        self,
        relative_path: str,
        raw_bytes: bytes,
        *,
        root_anchor: DirectoryAnchor | LockedRoot | None = None,
    ) -> None:
        """Testable exact publication seam used only after event verification."""

        self.write_relative(relative_path, raw_bytes, root_anchor=root_anchor)

    def stage_recovery_marker(self, command: dict[str, Any], relative_path: str, raw_bytes: bytes) -> bytes:
        marker = _recovery_marker(command, relative_path, raw_bytes)
        marker_bytes = canonical_bytes(marker)
        with self._open_directory(self.recovery_directory, create=True) as directory:
            directory.write_exact_file(_marker_name(command), marker_bytes)
        return marker_bytes

    @contextmanager
    def recovery_session(self) -> Iterator[tuple[DirectoryAnchor, DirectoryAnchor]]:
        """Hold the exact physical recovery directory for one complete pass."""

        root = open_registered_root_anchor(self.control_root, delete_protect=True)
        primary_error: BaseException | None = None
        try:
            with self._open_directory(
                self.recovery_directory,
                create=True,
                root_anchor=root,
            ) as directory:
                yield root, directory
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                root.close()
            except BaseException as cleanup_error:
                if primary_error is not None:
                    raise primary_error.with_traceback(primary_error.__traceback__) from cleanup_error
                raise

    @staticmethod
    def recovery_markers(directory: DirectoryAnchor) -> tuple[tuple[str, bytes], ...]:
        names = directory.list_names()
        return tuple((name, directory.read_regular_file(name)) for name in names if name.endswith(".json"))

    def remove_recovery_marker(
        self,
        command: dict[str, Any],
        marker_bytes: bytes,
        *,
        directory: DirectoryAnchor | None = None,
    ) -> None:
        if directory is not None:
            directory.remove_exact_file(_marker_name(command), marker_bytes)
            return
        with self.recovery_session() as (_root, opened):
            opened.remove_exact_file(_marker_name(command), marker_bytes)

    def marker_exists(self, command: dict[str, Any]) -> bool:
        with self.recovery_session() as (_root, directory):
            return _marker_name(command) in directory.list_names()


_COMMAND_FIELDS = {
    "command_id",
    "command_type",
    "schema_id",
    "schema_version",
    "submitted_at",
    "actor_id",
    "on_behalf_of_actor_id",
    "authority_grant_id",
    "target_stream_id",
    "expected_stream_version",
    "idempotency_key",
    "correlation_id",
    "causation_id",
    "reason",
    "evidence_refs",
    "payload",
    "project_id",
}


@dataclass(frozen=True)
class _PreparedRecovery:
    command: dict[str, Any]
    relative_path: str
    raw_bytes: bytes
    marker_bytes: bytes


def _marker_name(command: Mapping[str, Any]) -> str:
    command_id = command.get("command_id")
    if not isinstance(command_id, str) or not command_id.startswith("cmd_"):
        raise IntegrityError("registered content marker command identity is invalid")
    return f"{command_id}.json"


def _recovery_marker(command: dict[str, Any], relative_path: str, raw_bytes: bytes) -> dict[str, Any]:
    body = {
        "marker_version": "1.0.0",
        "command": deepcopy(command),
        "relative_path": relative_path,
        "content_sha256": sha256_hex(raw_bytes),
        "content_base64": base64.b64encode(raw_bytes).decode("ascii"),
    }
    return {**body, "marker_sha256": sha256_hex(canonical_bytes(body))}


def _decode_recovery_marker(name: str, raw: bytes) -> _PreparedRecovery:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("registered content recovery marker is not canonical JSON") from exc
    if not isinstance(value, dict) or canonical_bytes(value) != raw:
        raise IntegrityError("registered content recovery marker is not canonical JSON")
    required = {
        "marker_version",
        "command",
        "relative_path",
        "content_sha256",
        "content_base64",
        "marker_sha256",
    }
    if set(value) != required or value.get("marker_version") != "1.0.0":
        raise IntegrityError("registered content recovery marker shape is invalid")
    body = {key: value[key] for key in required if key != "marker_sha256"}
    if value.get("marker_sha256") != sha256_hex(canonical_bytes(body)):
        raise IntegrityError("registered content recovery marker hash mismatch")
    command = value.get("command")
    relative_path = value.get("relative_path")
    if not isinstance(command, dict) or set(command) != _COMMAND_FIELDS or not isinstance(relative_path, str):
        raise IntegrityError("registered content recovery command is invalid")
    if name != _marker_name(command):
        raise IntegrityError("registered content recovery marker name mismatch")
    try:
        raw_bytes = base64.b64decode(value.get("content_base64"), validate=True)
        payload_hash = Command(command).payload_hash
    except (TypeError, ValueError) as exc:
        raise IntegrityError("registered content recovery marker encoding is invalid") from exc
    payload = command.get("payload")
    manifest = payload.get("manifest") if isinstance(payload, dict) else None
    if (
        command.get("command_type") != "RegisterArtefact"
        or command.get("schema_id") != "ars://core/command/RegisterArtefact"
        or command.get("schema_version") != "1.0.0"
        or command.get("expected_stream_version") != 0
        or not isinstance(manifest, dict)
        or payload.get("new_artefact_id") != command.get("target_stream_id")
        or manifest.get("artefact_id") != command.get("target_stream_id")
        or manifest.get("relative_path") != relative_path
        or manifest.get("size_bytes") != len(raw_bytes)
        or manifest.get("content_sha256") != sha256_hex(raw_bytes)
        or value.get("content_sha256") != sha256_hex(raw_bytes)
        or payload_hash != sha256_hex(canonical_bytes(payload))
    ):
        raise IntegrityError("registered content recovery marker binding is invalid")
    CandidateDocumentStore._relative_file(relative_path)
    return _PreparedRecovery(deepcopy(command), relative_path, raw_bytes, raw)


def _registration_event_matches(event: object, command: dict[str, Any]) -> bool:
    if not isinstance(event, Mapping):
        return False
    return (
        event.get("command_id") == command["command_id"]
        and event.get("command_type") == "RegisterArtefact"
        and event.get("event_type") == "ArtefactRegistered"
        and event.get("stream_id") == command["target_stream_id"]
        and event.get("project_id") == command["project_id"]
        and event.get("command_schema_id") == command["schema_id"]
        and event.get("command_schema_version") == command["schema_version"]
        and event.get("idempotency_key") == command["idempotency_key"]
        and event.get("correlation_id") == command["correlation_id"]
        and event.get("causation_id") == command["causation_id"]
        and event.get("actor_id") == command["actor_id"]
        and event.get("authority_grant_id") == command["authority_grant_id"]
        and event.get("command_payload_hash") == Command(command).payload_hash
        and event.get("payload") == command["payload"]
    )


def _after_recovery_directory_anchored(_directory: DirectoryAnchor) -> None:
    """Test seam after the physical recovery directory is held."""


def recover_registered_content(
    document_store: CandidateDocumentStore,
    events: tuple[dict[str, Any], ...],
) -> tuple[str, ...]:
    """Publish staged content only from one exact committed registration event."""

    with document_store.recovery_session() as (root, directory):
        _after_recovery_directory_anchored(directory)
        prepared = tuple(_decode_recovery_marker(name, raw) for name, raw in document_store.recovery_markers(directory))
        authorized: list[_PreparedRecovery] = []
        for item in prepared:
            matches = [event for event in events if _registration_event_matches(event, item.command)]
            if len(matches) > 1:
                raise IntegrityError("registered content recovery found duplicate registration events")
            if len(matches) == 1:
                authorized.append(item)
        for item in authorized:
            document_store.publish_registered(
                item.relative_path,
                item.raw_bytes,
                root_anchor=root,
            )
            if document_store.read_relative(item.relative_path, root_anchor=root) != item.raw_bytes:
                raise IntegrityError("registered content publication does not match the authorized bytes")
            document_store.remove_recovery_marker(
                item.command,
                item.marker_bytes,
                directory=directory,
            )
    return tuple(item.relative_path for item in authorized)


__all__ = ["CandidateDocumentStore", "recover_registered_content"]
