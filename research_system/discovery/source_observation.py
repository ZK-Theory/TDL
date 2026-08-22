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
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry
from research_system.store.lock import LockedRoot
from research_system.store.registered_content import CandidateDocumentStore


_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_OID = re.compile(r"[0-9a-f]{40}")
_SOURCE_REFERENCE_FIELDS = {
    "ref_kind",
    "artefact_id",
    "content_hash",
    "registration_event_id",
    "registration_event_hash",
    "registration_global_position",
}
_SOURCE_VALIDATION_REF_PREFIX = "spec-source-"
_SOURCE_VALIDATION_REF_FIELDS = {
    "replay_binding_sha256": "spec-source-replay-binding-sha256:",
    "route_id": "spec-source-route-id:",
    "source_bundle_sha256": "spec-source-bundle-sha256:",
    "causal_position": "spec-source-causal-position:",
    "causal_event_hash": "spec-source-causal-event-hash:",
    "causal_raw_prefix_sha256": "spec-source-causal-raw-prefix-sha256:",
}


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


def _source_replay_binding_sha256(
    *,
    source_observation_id: str,
    producer_actor_id: str,
    observed_at: str,
    requested_locator: str,
    commit_oid: str,
) -> str:
    return sha256_hex(
        canonical_bytes(
            {
                "source_observation_id": source_observation_id,
                "producer_actor_id": producer_actor_id,
                "observed_at": observed_at,
                "requested_locator": requested_locator,
                "commit_oid": commit_oid,
            }
        )
    )


def registered_source_manifest_evidence(manifest: Mapping[str, object]) -> dict[str, object]:
    """Decode the closed SPEC-source evidence carried by existing validation refs."""

    validation = manifest.get("validation")
    refs = validation.get("validation_record_refs") if isinstance(validation, Mapping) else None
    if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
        raise IntegrityError("Scout source artefact registration binding is invalid")
    values: dict[str, list[str]] = {field: [] for field in _SOURCE_VALIDATION_REF_FIELDS}
    for ref in refs:
        if not ref.startswith(_SOURCE_VALIDATION_REF_PREFIX):
            continue
        matches = [(field, prefix) for field, prefix in _SOURCE_VALIDATION_REF_FIELDS.items() if ref.startswith(prefix)]
        if len(matches) != 1:
            raise IntegrityError("Scout source artefact registration binding is invalid")
        field, prefix = matches[0]
        values[field].append(ref[len(prefix) :])
    if any(len(field_values) != 1 for field_values in values.values()):
        raise IntegrityError("Scout source artefact registration binding is invalid")

    replay_binding_sha256 = values["replay_binding_sha256"][0]
    route_id = values["route_id"][0]
    source_bundle_sha256 = values["source_bundle_sha256"][0]
    causal_position_text = values["causal_position"][0]
    causal_event_hash = values["causal_event_hash"][0]
    causal_raw_prefix_sha256 = values["causal_raw_prefix_sha256"][0]
    try:
        causal_position = int(causal_position_text)
    except ValueError as exc:
        raise IntegrityError("Scout source artefact causal binding is invalid") from exc
    if (
        _SHA256.fullmatch(replay_binding_sha256) is None
        or not route_id
        or _SHA256.fullmatch(source_bundle_sha256) is None
        or causal_position < 0
        or str(causal_position) != causal_position_text
        or _SHA256.fullmatch(causal_event_hash) is None
        or _SHA256.fullmatch(causal_raw_prefix_sha256) is None
        or (causal_position == 0 and causal_event_hash != "0" * 64)
    ):
        raise IntegrityError("Scout source artefact causal binding is invalid")
    return {
        "replay_binding_sha256": replay_binding_sha256,
        "route_id": route_id,
        "source_bundle_sha256": source_bundle_sha256,
        "causal_ledger_prefix": {
            "global_position": causal_position,
            "event_hash": causal_event_hash,
            "raw_prefix_sha256": causal_raw_prefix_sha256,
        },
    }


def validate_registered_source_reference(
    reference: object,
    artefact: object,
    *,
    observation_position: object,
    observation_id: object,
    source_query: object,
    source_version: object,
    observed_at: object,
) -> Mapping[str, object]:
    """Validate the complete replayable binding to one registered source document."""

    if not isinstance(reference, Mapping) or set(reference) != _SOURCE_REFERENCE_FIELDS:
        raise IntegrityError("Scout source artefact reference is not exact")
    position = reference.get("registration_global_position")
    if (
        reference.get("ref_kind") != "artefact"
        or not isinstance(reference.get("artefact_id"), str)
        or not isinstance(reference.get("registration_event_id"), str)
        or type(position) is not int
        or position < 1
        or type(observation_position) is not int
        or observation_position < 1
        or position >= observation_position
        or not isinstance(reference.get("content_hash"), str)
        or _SHA256.fullmatch(reference.get("content_hash", "")) is None
        or not isinstance(reference.get("registration_event_hash"), str)
        or _SHA256.fullmatch(reference.get("registration_event_hash", "")) is None
        or not isinstance(observation_id, str)
        or not observation_id
        or not isinstance(source_query, str)
        or not source_query
        or not isinstance(source_version, str)
        or _GIT_OID.fullmatch(source_version) is None
        or not isinstance(observed_at, str)
    ):
        raise IntegrityError("Scout source artefact reference is invalid")
    try:
        validate_id(reference.get("artefact_id"), "artefact")
        validate_id(reference.get("registration_event_id"), "event")
    except (TypeError, ValueError) as exc:
        raise IntegrityError("Scout source artefact reference identity is invalid") from exc
    if not isinstance(artefact, Mapping):
        raise IntegrityError("Scout source artefact registration binding is invalid")
    manifest = artefact.get("manifest")
    producer_actor_id = manifest.get("producer_actor_id") if isinstance(manifest, Mapping) else None
    try:
        if isinstance(producer_actor_id, str):
            validate_id(producer_actor_id, "actor")
    except ValueError as exc:
        raise IntegrityError("Scout source artefact producer identity is invalid") from exc
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("artefact_type") != "spec_source_observation"
        or manifest.get("artefact_schema_id") != "ars://portfolio/spec-source-observation"
        or manifest.get("artefact_schema_version") != "1.0.0"
        or reference.get("artefact_id") != manifest.get("artefact_id")
        or reference.get("content_hash") != artefact.get("content_sha256")
        or reference.get("registration_event_id") != artefact.get("registration_event_id")
        or reference.get("registration_event_hash") != artefact.get("registration_event_hash")
        or position != artefact.get("registration_global_position")
        or not isinstance(producer_actor_id, str)
        or producer_actor_id != artefact.get("registration_actor_id")
        or manifest.get("observed_at") != observed_at
    ):
        raise IntegrityError("Scout source artefact registration binding is invalid")
    evidence = registered_source_manifest_evidence(manifest)
    prefix = evidence["causal_ledger_prefix"]
    assert isinstance(prefix, dict)
    prefix_position = prefix["global_position"]
    assert isinstance(prefix_position, int)
    if prefix_position >= position or evidence["replay_binding_sha256"] != _source_replay_binding_sha256(
        source_observation_id=observation_id,
        producer_actor_id=producer_actor_id,
        observed_at=observed_at,
        requested_locator=source_query,
        commit_oid=source_version,
    ):
        raise IntegrityError("Scout source artefact causal binding is invalid")
    return manifest


def source_observation_manifest_references(document: Mapping[str, object]) -> tuple[str, ...]:
    """Return the closed replay-visible provenance copied into validation refs."""

    resolution = document.get("resolution")
    prefix = document.get("causal_ledger_prefix")
    if not isinstance(resolution, Mapping) or not isinstance(prefix, Mapping):
        raise IntegrityError("SPEC source observation cannot form a registration binding")
    source_observation_id = document.get("source_observation_id")
    route_id = document.get("route_id")
    producer_actor_id = document.get("producer_actor_id")
    observed_at = document.get("observed_at")
    requested_locator = resolution.get("requested_locator")
    commit_oid = resolution.get("commit_oid")
    source_bundle_sha256 = document.get("source_bundle_sha256")
    causal_position = prefix.get("global_position")
    causal_event_hash = prefix.get("event_hash")
    causal_raw_prefix_sha256 = prefix.get("raw_prefix_sha256")
    if (
        not all(
            isinstance(value, str) and value
            for value in (
                source_observation_id,
                route_id,
                producer_actor_id,
                observed_at,
                requested_locator,
                commit_oid,
            )
        )
        or not isinstance(source_bundle_sha256, str)
        or _SHA256.fullmatch(source_bundle_sha256) is None
        or type(causal_position) is not int
        or causal_position < 0
        or not isinstance(causal_event_hash, str)
        or _SHA256.fullmatch(causal_event_hash) is None
        or not isinstance(causal_raw_prefix_sha256, str)
        or _SHA256.fullmatch(causal_raw_prefix_sha256) is None
        or (causal_position == 0 and causal_event_hash != "0" * 64)
    ):
        raise IntegrityError("SPEC source observation cannot form a registration binding")
    assert isinstance(source_observation_id, str)
    assert isinstance(route_id, str)
    assert isinstance(producer_actor_id, str)
    assert isinstance(observed_at, str)
    assert isinstance(requested_locator, str)
    assert isinstance(commit_oid, str)
    return (
        _SOURCE_VALIDATION_REF_FIELDS["replay_binding_sha256"]
        + _source_replay_binding_sha256(
            source_observation_id=source_observation_id,
            producer_actor_id=producer_actor_id,
            observed_at=observed_at,
            requested_locator=requested_locator,
            commit_oid=commit_oid,
        ),
        _SOURCE_VALIDATION_REF_FIELDS["route_id"] + route_id,
        _SOURCE_VALIDATION_REF_FIELDS["source_bundle_sha256"] + source_bundle_sha256,
        _SOURCE_VALIDATION_REF_FIELDS["causal_position"] + str(causal_position),
        _SOURCE_VALIDATION_REF_FIELDS["causal_event_hash"] + causal_event_hash,
        _SOURCE_VALIDATION_REF_FIELDS["causal_raw_prefix_sha256"] + causal_raw_prefix_sha256,
    )


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
        or type(manifest.get("size_bytes")) is not int
        or manifest.get("size_bytes", -1) < 0
        or not isinstance(manifest.get("producer_actor_id"), str)
        or not isinstance(manifest.get("observed_at"), str)
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
    document = validate_spec_source_observation(value, schemas=schemas)
    registered_source_manifest_evidence(manifest)
    validation = manifest.get("validation")
    validation_refs = validation.get("validation_record_refs") if isinstance(validation, Mapping) else None
    manifest_source_refs = {
        ref for ref in validation_refs or [] if isinstance(ref, str) and ref.startswith(_SOURCE_VALIDATION_REF_PREFIX)
    }
    if (
        document.get("producer_actor_id") != manifest.get("producer_actor_id")
        or document.get("observed_at") != manifest.get("observed_at")
        or set(source_observation_manifest_references(document)) != manifest_source_refs
    ):
        raise IntegrityError("registered SPEC source observation provenance does not match the manifest")
    return document


__all__ = [
    "CausalLedgerPrefix",
    "SourceReferenceNotResolved",
    "prepare_spec_source_observation",
    "read_registered_spec_source_observation",
    "registered_source_manifest_evidence",
    "source_observation_manifest_references",
    "validate_registered_source_reference",
    "validate_spec_source_observation",
]
