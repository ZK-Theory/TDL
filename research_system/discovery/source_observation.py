"""Prepare immutable source observations from exact remote Git bytes."""

from __future__ import annotations

import base64
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.git_reference import (
    GitReferenceResolution,
    GitSourceTransport,
    resolve_github_reference,
)
from research_system.errors import ArsError, ConfigurationError, IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry
from research_system.store.lock import LockedRoot
from research_system.store.registered_content import CandidateDocumentStore


_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class CausalLedgerPrefix:
    """Exact persisted ledger prefix that justified a source observation."""

    global_position: int
    event_hash: str
    raw_prefix_sha256: str

    def __post_init__(self) -> None:
        if type(self.global_position) is not int or self.global_position < 0:
            raise ConfigurationError("causal ledger prefix position is invalid")
        if _SHA256.fullmatch(self.event_hash) is None or _SHA256.fullmatch(self.raw_prefix_sha256) is None:
            raise ConfigurationError("causal ledger prefix hash is invalid")
        if self.global_position == 0 and self.event_hash != "0" * 64:
            raise ConfigurationError("empty causal ledger prefix requires the genesis hash")

    def to_dict(self) -> dict[str, int | str]:
        return {
            "global_position": self.global_position,
            "event_hash": self.event_hash,
            "raw_prefix_sha256": self.raw_prefix_sha256,
        }


class SourceReferenceNotResolved(ArsError):
    """The requested source locator did not resolve to one exact commit."""

    def __init__(self, resolution: GitReferenceResolution) -> None:
        super().__init__(f"source reference is {resolution.status}")
        self.resolution = resolution


def _canonical_source_paths(required_paths: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(required_paths, tuple) or not required_paths:
        raise ConfigurationError("required source paths must be a non-empty tuple")
    for value in required_paths:
        if not isinstance(value, str):
            raise ConfigurationError("required source path must be a string")
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or path.as_posix() != value
            or any(part in {"", ".", ".."} for part in path.parts)
            or "\\" in value
            or ":" in value
        ):
            raise ConfigurationError("required source path must be canonical and repository-relative")
    if len(required_paths) != len(set(required_paths)):
        raise ConfigurationError("required source paths must be unique")
    return tuple(sorted(required_paths))


def _require_observed_at(value: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ConfigurationError("source observation time must be UTC")
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigurationError("source observation time is invalid") from exc
    if observed.utcoffset() is None or observed.utcoffset().total_seconds() != 0:
        raise ConfigurationError("source observation time must be UTC")


def prepare_spec_source_observation(
    *,
    locator: str,
    required_paths: tuple[str, ...],
    source_observation_id: str,
    route_id: str,
    producer_actor_id: str,
    observed_at: str,
    causal_prefix: CausalLedgerPrefix,
    transport: GitSourceTransport,
    schemas: SchemaRegistry,
) -> dict[str, object]:
    """Resolve, read, hash, and schema-validate one exact SPEC source document."""

    paths = _canonical_source_paths(required_paths)
    _require_observed_at(observed_at)
    resolution = resolve_github_reference(locator, transport=transport)
    if resolution.status != "resolved":
        raise SourceReferenceNotResolved(resolution)
    assert resolution.commit_oid is not None
    source_bytes = transport.read_paths(resolution.repository_url, resolution.commit_oid, paths)
    if set(source_bytes) != set(paths):
        missing = sorted(set(paths) - set(source_bytes))
        unexpected = sorted(set(source_bytes) - set(paths))
        detail = f"missing={missing}, unexpected={unexpected}"
        raise IntegrityError(f"required source paths were not returned exactly ({detail})")

    files: list[dict[str, object]] = []
    for path in paths:
        raw = source_bytes[path]
        if not isinstance(raw, bytes):
            raise IntegrityError("required source path did not return bytes")
        files.append(
            {
                "path": path,
                "size_bytes": len(raw),
                "content_sha256": sha256_hex(raw),
                "content_base64": base64.b64encode(raw).decode("ascii"),
            }
        )
    document: dict[str, object] = {
        "schema_id": "ars://portfolio/spec-source-observation",
        "schema_version": "1.0.0",
        "document_type": "spec_source_observation",
        "source_observation_id": source_observation_id,
        "route_id": route_id,
        "producer_actor_id": producer_actor_id,
        "observed_at": observed_at,
        "causal_ledger_prefix": causal_prefix.to_dict(),
        "resolution": resolution.to_dict(),
        "source_files": files,
        "source_bundle_sha256": sha256_hex(canonical_bytes(files)),
    }
    return validate_spec_source_observation(document, schemas=schemas)


def validate_spec_source_observation(
    value: object,
    *,
    schemas: SchemaRegistry,
) -> dict[str, object]:
    """Independently validate all byte/hash relations in a source document."""

    if not isinstance(value, dict):
        raise IntegrityError("SPEC source observation must be an object")
    try:
        schemas.validate(
            "ars://portfolio/spec-source-observation",
            value,
            schema_version="1.0.0",
        )
        resolution = GitReferenceResolution.from_dict(value["resolution"])
        prefix = value["causal_ledger_prefix"]
        CausalLedgerPrefix(
            global_position=prefix["global_position"],
            event_hash=prefix["event_hash"],
            raw_prefix_sha256=prefix["raw_prefix_sha256"],
        )
    except (ConfigurationError, KeyError, SchemaError, TypeError) as exc:
        raise IntegrityError("SPEC source observation schema or provenance is invalid") from exc
    if resolution.status != "resolved":
        raise IntegrityError("SPEC source observation requires one resolved Git reference")
    files = value.get("source_files")
    if not isinstance(files, list):
        raise IntegrityError("SPEC source observation files are invalid")
    paths: list[str] = []
    for item in files:
        if not isinstance(item, dict):
            raise IntegrityError("SPEC source observation file is invalid")
        try:
            raw = base64.b64decode(item["content_base64"], validate=True)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("SPEC source observation file encoding is invalid") from exc
        if item.get("size_bytes") != len(raw) or item.get("content_sha256") != sha256_hex(raw):
            raise IntegrityError("SPEC source observation file hash or size mismatch")
        paths.append(str(item.get("path")))
    try:
        canonical_paths = _canonical_source_paths(tuple(paths))
    except ConfigurationError as exc:
        raise IntegrityError("SPEC source observation file paths are invalid") from exc
    if tuple(paths) != canonical_paths or value.get("source_bundle_sha256") != sha256_hex(canonical_bytes(files)):
        raise IntegrityError("SPEC source observation bundle binding is invalid")
    return deepcopy(value)


def read_registered_spec_source_observation(
    *,
    control_root: Path,
    manifest: Mapping[str, object],
    schemas: SchemaRegistry,
    locked_root: LockedRoot | None = None,
) -> dict[str, object]:
    """Read one registered source document through its exact anchored manifest."""

    if (
        manifest.get("artefact_type") != "spec_source_observation"
        or manifest.get("artefact_schema_id") != "ars://portfolio/spec-source-observation"
        or manifest.get("artefact_schema_version") != "1.0.0"
        or not isinstance(manifest.get("relative_path"), str)
        or not isinstance(manifest.get("content_sha256"), str)
        or not isinstance(manifest.get("size_bytes"), int)
    ):
        raise IntegrityError("registered SPEC source observation manifest is invalid")
    raw = CandidateDocumentStore(control_root).read_relative(
        str(manifest["relative_path"]),
        root_anchor=locked_root,
    )
    if len(raw) != manifest["size_bytes"] or sha256_hex(raw) != manifest["content_sha256"]:
        raise IntegrityError("registered SPEC source observation bytes do not match the manifest")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("registered SPEC source observation is not JSON") from exc
    if canonical_bytes(value) != raw:
        raise IntegrityError("registered SPEC source observation is not canonical JSON")
    return validate_spec_source_observation(value, schemas=schemas)


__all__ = [
    "CausalLedgerPrefix",
    "SourceReferenceNotResolved",
    "prepare_spec_source_observation",
    "read_registered_spec_source_observation",
    "validate_spec_source_observation",
]
