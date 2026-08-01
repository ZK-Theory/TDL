from __future__ import annotations

import errno
import json
import os
import secrets
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import new_id, validate_id
from research_system.schema_registry import (
    SchemaRegistry,
    bundled_runtime_schema_registry,
    require_authority_schemas,
    runtime_schema_registry,
)
from research_system.store.identity import SCHEMA_BINDING_VERSION


_GRANT_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "authority_grant_id",
        "actor_id",
        "allowed_command_types",
        "subject_scope",
        "risk_ceiling",
        "effective_at",
        "expires_at",
        "delegable",
        "revoked",
    }
)
_SUBJECT_KINDS = {
    "authority_grant": "authority_grant",
    "release_gate_decision": "release_gate_decision",
    "assurance_requirement": "assurance_requirement",
}


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be a UTC RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} must be a UTC RFC 3339 timestamp") from exc
    if parsed.tzinfo != UTC:
        raise ValueError(f"{field} must use UTC")
    return parsed


@dataclass(frozen=True)
class AuthorityScope:
    """Canonical project and subject tuple governed by an authority grant.

    Attributes:
        project_id: Project identity containing the governed subject.
        subject_kind: Registered governed subject kind.
        subject_id: Exact governed subject identity.
    """

    project_id: str
    subject_kind: str
    subject_id: str

    @classmethod
    def from_dict(cls, value: object) -> AuthorityScope:
        """Build and validate an exact typed authority scope.

        Args:
            value: Candidate scope mapping.

        Returns:
            The validated immutable scope.

        Raises:
            ValueError: If the mapping, project, kind, or subject ID is invalid.
        """
        if not isinstance(value, dict) or set(value) != {"project_id", "subject"}:
            raise ValueError("subject_scope fields must be exact")
        subject = value["subject"]
        if not isinstance(subject, dict) or set(subject) != {"kind", "id"}:
            raise ValueError("subject fields must be exact")
        project_id = validate_id(str(value["project_id"]), "project")
        kind = subject["kind"]
        if kind not in _SUBJECT_KINDS:
            raise ValueError("unsupported authority subject kind")
        subject_id = validate_id(str(subject["id"]), _SUBJECT_KINDS[kind])
        return cls(project_id, str(kind), subject_id)

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical JSON-compatible scope representation.

        Returns:
            A project mapping containing the typed subject mapping.
        """
        return {
            "project_id": self.project_id,
            "subject": {"kind": self.subject_kind, "id": self.subject_id},
        }


@dataclass(frozen=True)
class AuthorityGrant:
    """Validated immutable AuthorityGrant 1.1.0 object.

    Attributes:
        authority_grant_id: Canonical grant identity.
        actor_id: Attributed actor identity.
        allowed_command_types: Exact command names governed by the grant.
        subject_scope: Typed project and subject scope.
        risk_ceiling: Closed maximum risk tier.
        effective_at: Inclusive trusted UTC activation time.
        expires_at: Exclusive trusted UTC expiry, if any.
        canonical_sha256: Digest of the canonical grant representation.
    """

    authority_grant_id: str
    actor_id: str
    allowed_command_types: tuple[str, ...]
    subject_scope: AuthorityScope
    risk_ceiling: str
    effective_at: datetime
    expires_at: datetime | None
    canonical_sha256: str

    @classmethod
    def from_dict(cls, value: object) -> AuthorityGrant:
        """Build an immutable grant from its exact canonical representation.

        Args:
            value: Candidate AuthorityGrant mapping.

        Returns:
            The validated grant with its canonical SHA-256 digest.

        Raises:
            ValueError: If any field or cross-field invariant is invalid.
        """
        canonical_bytes(value)
        if not isinstance(value, dict) or set(value) != _GRANT_FIELDS:
            raise ValueError("AuthorityGrant fields must be exact")
        if value["schema_id"] != "ars://core/authority-grant":
            raise ValueError("invalid AuthorityGrant schema")
        if value["schema_version"] != "1.1.0":
            raise ValueError("AuthorityGrant 1.1.0 is required")
        if value["delegable"] is not False or value["revoked"] is not False:
            raise ValueError("AuthorityGrant must be non-delegable and immutable-active")
        grant_id = validate_id(str(value["authority_grant_id"]), "authority_grant")
        actor_id = validate_id(str(value["actor_id"]), "actor")
        commands = value["allowed_command_types"]
        if (
            not isinstance(commands, list)
            or not commands
            or not all(
                isinstance(command, str)
                and command
                and command.isascii()
                and command != "*"
                and "/" not in command
                and "\\" not in command
                for command in commands
            )
        ):
            raise ValueError("allowed command types must be unique exact ASCII names")
        if len(commands) != len(set(commands)):
            raise ValueError("allowed command types must be unique exact ASCII names")
        risk = value["risk_ceiling"]
        if not isinstance(risk, str) or risk not in {"R0", "R1", "R2", "R3"}:
            raise ValueError("invalid risk ceiling")
        effective_at = _utc(value["effective_at"], "effective_at")
        expires_at = None if value["expires_at"] is None else _utc(value["expires_at"], "expires_at")
        if expires_at is not None and expires_at <= effective_at:
            raise ValueError("expires_at must be strictly after effective_at")
        scope = AuthorityScope.from_dict(value["subject_scope"])
        return cls(
            authority_grant_id=grant_id,
            actor_id=actor_id,
            allowed_command_types=tuple(commands),
            subject_scope=scope,
            risk_ceiling=risk,
            effective_at=effective_at,
            expires_at=expires_at,
            canonical_sha256=sha256_hex(canonical_bytes(value)),
        )


@dataclass(frozen=True)
class AuthorityGrantResolution:
    """Replay-derived immutable identity plus current grant status.

    Attributes:
        authority_grant_id: Resolved grant identity.
        authority_grant_sha256: Canonical immutable grant digest.
        actor_id: Attributed actor bound by the grant.
        subject_scope: Exact typed governed scope.
        effective_at: Inclusive trusted UTC activation time.
        expires_at: Exclusive trusted UTC expiry, if any.
        activation_event_id: Ledger event that activated the grant.
        activation_position: Global ledger position of activation.
        status: Current replay-derived grant status.
        revocation_event_id: Revocation event identity, if revoked.
    """

    authority_grant_id: str
    authority_grant_sha256: str
    actor_id: str
    subject_scope: AuthorityScope
    effective_at: datetime
    expires_at: datetime | None
    activation_event_id: str
    activation_position: int
    status: str
    revocation_event_id: str | None


def authority_bootstrap_sha256(value: object) -> str:
    """Return the canonical SHA-256 digest of an authority bootstrap value.

    Args:
        value: JSON-compatible bootstrap value.

    Returns:
        Lowercase hexadecimal SHA-256 digest.

    Raises:
        ValueError: If the value is not canonical JSON-compatible.
    """
    return sha256_hex(canonical_bytes(value))


def _manifest_hash(manifest: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"}))


def _validate_bootstrap(value: object, project_id: str) -> tuple[dict[str, Any], AuthorityGrant, AuthorityGrant]:
    canonical_bytes(value)
    fields = {
        "schema_id",
        "schema_version",
        "project_id",
        "owner_actor_id",
        "root_grant",
        "root_grant_sha256",
        "publication_grant",
        "publication_grant_sha256",
        "publication_target_id",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("authority bootstrap fields must be exact")
    if value["schema_id"] != "ars://core/authority-bootstrap-manifest" or value["schema_version"] != "1.0.0":
        raise ValueError("invalid authority bootstrap schema")
    if validate_id(str(value["project_id"]), "project") != project_id:
        raise ValueError("authority bootstrap project mismatch")
    owner = validate_id(str(value["owner_actor_id"]), "actor")
    root = AuthorityGrant.from_dict(value["root_grant"])
    publication = AuthorityGrant.from_dict(value["publication_grant"])
    target = validate_id(str(value["publication_target_id"]), "release_gate_decision")
    if root.actor_id != owner or publication.actor_id != owner:
        raise ValueError("authority bootstrap actor mismatch")
    if (
        root.canonical_sha256 != value["root_grant_sha256"]
        or publication.canonical_sha256 != value["publication_grant_sha256"]
    ):
        raise ValueError("authority bootstrap grant hash mismatch")
    if root.allowed_command_types != ("RevokeAuthorityGrant",):
        raise ValueError("administrative root command scope mismatch")
    if root.subject_scope != AuthorityScope(project_id, "authority_grant", publication.authority_grant_id):
        raise ValueError("administrative root subject scope mismatch")
    if publication.allowed_command_types != ("PublishReleaseGateDecision",):
        raise ValueError("publication command scope mismatch")
    if publication.subject_scope != AuthorityScope(project_id, "release_gate_decision", target):
        raise ValueError("publication subject scope mismatch")
    if publication.expires_at is None:
        raise ValueError("publication grant requires expiry")
    return dict(value), root, publication


def _verify_grant_object(
    control_root: Path,
    grant: AuthorityGrant,
    expected_value: object,
) -> None:
    directory = control_root / "objects" / "authority_grant" / grant.authority_grant_id
    matches = sorted(directory.glob("00000001-*.json"))
    expected_name = f"00000001-{grant.canonical_sha256}.json"
    if (
        len(matches) != 1
        or matches[0].name != expected_name
        or matches[0].read_bytes() != canonical_bytes(expected_value)
    ):
        raise IntegrityError("authority bootstrap grant object mismatch")


def _verify_bootstrap_bindings(
    control_root: Path,
    project_id: str,
    bootstrap: object,
    events: tuple[dict[str, Any], ...],
    projection: dict[str, Any],
) -> None:
    try:
        value, root, publication = _validate_bootstrap(bootstrap, project_id)
    except ValueError as exc:
        raise IntegrityError("authority bootstrap manifest invalid") from exc
    bootstrap_hash = authority_bootstrap_sha256(value)
    _verify_grant_object(control_root, root, value["root_grant"])
    _verify_grant_object(control_root, publication, value["publication_grant"])
    if len(events) < 2:
        raise IntegrityError("authority bootstrap genesis missing")
    root_event, publication_event = events[:2]
    expected_common = {
        "command_type": "InitializeAuthorityRoot",
        "actor_id": value["owner_actor_id"],
        "authority_grant_id": root.authority_grant_id,
        "idempotency_key": f"authority-bootstrap:{bootstrap_hash}",
        "command_payload_hash": bootstrap_hash,
        "correlation_id": f"authority-bootstrap:{bootstrap_hash}",
        "causation_id": None,
    }
    for field, expected in expected_common.items():
        if root_event.get(field) != expected or publication_event.get(field) != expected:
            raise IntegrityError("authority bootstrap genesis envelope mismatch")
    if root_event.get("command_id") != publication_event.get("command_id"):
        raise IntegrityError("authority bootstrap genesis command mismatch")
    if (
        root_event.get("event_type") != "AuthorityRootInitialized"
        or root_event.get("schema_id") != "ars://core/event/AuthorityRootInitialized"
        or root_event.get("stream_id") != root.authority_grant_id
        or root_event.get("payload")
        != {
            "bootstrap_manifest_sha256": bootstrap_hash,
            "authorizing_grant_id": root.authority_grant_id,
            "authorizing_grant_sha256": root.canonical_sha256,
            "activated_grant_id": root.authority_grant_id,
            "activated_grant_sha256": root.canonical_sha256,
        }
    ):
        raise IntegrityError("authority bootstrap root binding mismatch")
    if (
        publication_event.get("event_type") != "AuthorityGrantActivated"
        or publication_event.get("schema_id") != "ars://core/event/AuthorityGrantActivated"
        or publication_event.get("stream_id") != publication.authority_grant_id
        or publication_event.get("payload")
        != {
            "authorizing_grant_id": root.authority_grant_id,
            "authorizing_grant_sha256": root.canonical_sha256,
            "activated_grant_id": publication.authority_grant_id,
            "activated_grant_sha256": publication.canonical_sha256,
        }
    ):
        raise IntegrityError("authority bootstrap publication binding mismatch")
    grants = projection.get("authority_grants", {})
    if (
        projection.get("project_id") != project_id
        or projection.get("bootstrap_manifest_sha256") != bootstrap_hash
        or projection.get("authority_root_id") != root.authority_grant_id
        or set(grants) != {root.authority_grant_id, publication.authority_grant_id}
        or grants[root.authority_grant_id].get("authority_grant_sha256") != root.canonical_sha256
        or grants[publication.authority_grant_id].get("authority_grant_sha256") != publication.canonical_sha256
    ):
        raise IntegrityError("authority bootstrap projection mismatch")


def _write_identity(
    stage: Path,
    final_root: Path,
    code_roots: list[Path],
    project_id: str,
    bootstrap_hash: str,
    schema_root: Path,
) -> str:
    nonce = secrets.token_hex(16)
    stable = {
        "schema_id": "ars://core/store-identity",
        "schema_version": "1.1.0",
        "store_nonce": nonce,
        "project_id": project_id,
        "bootstrap_manifest_sha256": bootstrap_hash,
    }
    identity = sha256_hex(canonical_bytes(stable))
    manifest: dict[str, Any] = {
        **stable,
        "store_identity": identity,
        "control_root": str(final_root.resolve(strict=False)),
        "code_roots": sorted(str(root.resolve(strict=True)) for root in code_roots),
        "endpoint_scheme": "local-cli",
    }
    manifest["schema_root"] = str(schema_root)
    manifest["schema_binding_version"] = SCHEMA_BINDING_VERSION
    manifest["manifest_hash"] = _manifest_hash(manifest)
    path = stage / "manifests" / "store-identity.json"
    with path.open("xb") as handle:
        handle.write(canonical_bytes(manifest))
        handle.flush()
        os.fsync(handle.fileno())
    return identity


def _bootstrap_failpoint(point: str) -> None:
    """Test seam overridden only by subprocess crash-boundary controls."""


def _write_durable(path: Path, data: bytes, *, exclusive: bool = False) -> None:
    mode = "xb" if exclusive else "wb"
    with path.open(mode) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
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


def _flush_tree(root: Path) -> None:
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        with path.open("r+b") as handle:
            os.fsync(handle.fileno())
    directories = [root, *(item for item in root.rglob("*") if item.is_dir())]
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        _fsync_directory(directory)


def _stage_marker(bootstrap_hash: str, status: str) -> dict[str, str]:
    return {
        "schema_id": "ars://core/authority-bootstrap-stage",
        "schema_version": "1.0.0",
        "bootstrap_manifest_sha256": bootstrap_hash,
        "status": status,
    }


def _write_stage_marker(stage: Path, bootstrap_hash: str, status: str) -> None:
    path = stage / "runtime" / "authority-bootstrap-stage.json"
    temporary = path.with_suffix(".json.tmp")
    _write_durable(temporary, canonical_bytes(_stage_marker(bootstrap_hash, status)))
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _remove_stage_marker(store_root: Path) -> None:
    path = store_root / "runtime" / "authority-bootstrap-stage.json"
    path.unlink(missing_ok=True)
    _fsync_directory(path.parent)


def _load_bound_manifest(store_root: Path, expected_control_root: Path) -> dict[str, Any]:
    path = store_root / "manifests" / "store-identity.json"
    try:
        data = path.read_bytes()
        manifest = json.loads(data)
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise IntegrityError("authority store identity manifest invalid") from exc
    if not isinstance(manifest, dict) or data != canonical_bytes(manifest):
        raise IntegrityError("authority store identity manifest is not canonical")
    if manifest.get("manifest_hash") != _manifest_hash(manifest):
        raise IntegrityError("authority store identity manifest hash mismatch")
    if manifest.get("control_root") != str(expected_control_root.resolve(strict=False)):
        raise IntegrityError("authority store control-root binding mismatch")
    stable = {
        "schema_id": manifest.get("schema_id"),
        "schema_version": manifest.get("schema_version"),
        "store_nonce": manifest.get("store_nonce"),
        "project_id": manifest.get("project_id"),
        "bootstrap_manifest_sha256": manifest.get("bootstrap_manifest_sha256"),
    }
    if (
        manifest.get("schema_id") != "ars://core/store-identity"
        or manifest.get("schema_version") != "1.1.0"
        or manifest.get("store_identity") != sha256_hex(canonical_bytes(stable))
    ):
        raise IntegrityError("authority store identity derivation mismatch")
    return manifest


def _read_event_batches(store_root: Path, project_id: str) -> tuple[tuple[dict[str, Any], ...], ...]:
    events_root = store_root / "events" / project_id
    if not events_root.is_dir():
        raise IntegrityError("authority event store missing")
    paths = list(events_root.rglob("*.jsonl"))
    try:
        paths.sort(key=lambda path: int(path.name.partition("-")[0]))
    except ValueError as exc:
        raise IntegrityError("authority event batch filename invalid") from exc
    batches: list[tuple[dict[str, Any], ...]] = []
    try:
        for path in paths:
            batch = tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
            if not batch:
                raise IntegrityError("authority event batch is empty")
            batches.append(batch)
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise IntegrityError("authority event batch invalid") from exc
    return tuple(batches)


def _verify_complete_store(
    store_root: Path,
    expected_control_root: Path,
    project_id: str,
    bootstrap: object,
    code_roots: list[Path],
    schemas: SchemaRegistry,
    expected_schema_root: Path | None,
    *,
    require_schema_binding: bool = False,
    require_genesis_only: bool = False,
) -> str:
    from research_system.projection.replay import replay

    try:
        value, _, _ = _validate_bootstrap(bootstrap, project_id)
    except ValueError as exc:
        raise IntegrityError("authority bootstrap manifest invalid") from exc
    bootstrap_bytes = canonical_bytes(value)
    bootstrap_hash = authority_bootstrap_sha256(value)
    manifest = _load_bound_manifest(store_root, expected_control_root)
    if manifest.get("project_id") != project_id or manifest.get("bootstrap_manifest_sha256") != bootstrap_hash:
        raise ConflictError("authority bootstrap conflicts with existing store")
    expected_roots = sorted(str(root.resolve(strict=True)) for root in code_roots)
    if manifest.get("code_roots") != expected_roots:
        raise ConflictError("authority store code root binding mismatch")
    from research_system.store.identity import manifest_schema_root

    persisted_schema_root = manifest_schema_root(manifest)
    if persisted_schema_root is None:
        if require_schema_binding:
            raise ConflictError("authority store schema root binding missing")
    elif expected_schema_root is None or persisted_schema_root != expected_schema_root:
        raise ConflictError("authority store schema root binding mismatch")
    bootstrap_path = store_root / "manifests" / "authority-bootstrap.json"
    try:
        stored_bootstrap = bootstrap_path.read_bytes()
    except OSError as exc:
        raise IntegrityError("authority bootstrap manifest missing") from exc
    if stored_bootstrap != bootstrap_bytes:
        raise IntegrityError("authority bootstrap manifest bytes mismatch")
    batches = _read_event_batches(store_root, project_id)
    if not batches or len(batches[0]) != 2:
        raise IntegrityError("authority genesis batch is split or incomplete")
    events = tuple(event for batch in batches for event in batch)
    if require_genesis_only and (len(batches) != 1 or len(events) != 2):
        raise IntegrityError("staged authority store contains non-genesis history")
    state = replay(events, schema_registry=schemas)
    _verify_bootstrap_bindings(store_root, project_id, value, events, state)
    return str(manifest["store_identity"])


def _matching_complete_stage(
    final_root: Path,
    project_id: str,
    bootstrap: object,
    bootstrap_hash: str,
    code_roots: list[Path],
    schemas: SchemaRegistry,
    schema_root: Path | None,
    *,
    require_schema_binding: bool,
) -> tuple[Path, str] | None:
    prefix = f".{final_root.name}.authority-stage-"
    for stage in sorted(final_root.parent.glob(f"{prefix}*")):
        marker_path = stage / "runtime" / "authority-bootstrap-stage.json"
        try:
            marker = json.loads(marker_path.read_bytes())
        except (OSError, json.JSONDecodeError, UnicodeError):
            continue
        if marker != _stage_marker(bootstrap_hash, "complete"):
            continue
        try:
            identity = _verify_complete_store(
                stage,
                final_root,
                project_id,
                bootstrap,
                code_roots,
                schemas,
                schema_root,
                require_schema_binding=require_schema_binding,
                require_genesis_only=True,
            )
        except (ArsError, OSError, ValueError):
            continue
        return stage, identity
    return None


def _authority_schema_registry(
    code_roots: list[Path],
    canonical_schema_root: Path | None = None,
    *,
    allow_bundled_fallback: bool = False,
) -> tuple[SchemaRegistry, Path | None]:
    """Resolve authority independently from the complete registered topology."""
    registered = {root / ".research-system" / "schemas" for root in code_roots}
    if canonical_schema_root is not None:
        if not canonical_schema_root.is_absolute() or canonical_schema_root not in registered:
            raise ArsError("canonical schema root must belong to a registered code root")
        if not canonical_schema_root.is_dir():
            raise ArsError("canonical schema root must be an existing directory")
        try:
            registry = require_authority_schemas(runtime_schema_registry(canonical_schema_root))
        except ArsError as exc:
            raise ArsError("canonical schema root is not a usable SchemaRegistry") from exc
        return registry, canonical_schema_root
    schema_roots = {root for root in registered if root.is_dir()}
    if len(schema_roots) > 1:
        raise ArsError("authority bootstrap requires one canonical schema root")
    if not schema_roots:
        if allow_bundled_fallback:
            return require_authority_schemas(bundled_runtime_schema_registry()), None
        raise ArsError("new authority store requires a registered schema root")
    schema_root = schema_roots.pop()
    return require_authority_schemas(runtime_schema_registry(schema_root)), schema_root


def initialize_authority_control_store(
    code_roots: list[Path],
    control_root: Path,
    project_id: str,
    bootstrap: object,
    approved_bootstrap_sha256: str,
    *,
    canonical_schema_root: Path | None = None,
) -> str:
    """Publish one complete authority-aware control store atomically.

    Args:
        code_roots: Registered and existing code worktree roots.
        control_root: Absent target directory for the canonical control store.
        project_id: Project identity bound into the store and ledger.
        bootstrap: Approved authority bootstrap manifest.
        approved_bootstrap_sha256: Operator-approved canonical manifest digest.
        canonical_schema_root: Explicit registered schema authority, when supplied.

    Returns:
        The published or exactly recovered store identity.

    Raises:
        ArsError: If inputs or an existing store fail authority requirements.
        ConflictError: If a competing publication is not the exact same store.
        IntegrityError: If staged or published authority history is incomplete.
        OSError: If staging or publication fails at the filesystem boundary.
    """
    from research_system.store.ledger import EventLedger
    from research_system.store.objects import ObjectStore

    project_id = validate_id(project_id, "project")
    value, root, publication = _validate_bootstrap(bootstrap, project_id)
    bootstrap_hash = authority_bootstrap_sha256(value)
    if approved_bootstrap_sha256 != bootstrap_hash:
        raise ArsError("approved authority bootstrap hash mismatch")
    final_root = control_root.parent.resolve(strict=True) / control_root.name
    resolved_codes = [root_path.resolve(strict=True) for root_path in code_roots]
    if not resolved_codes:
        raise ArsError("registered code roots required")
    if len(resolved_codes) != len(set(resolved_codes)):
        raise ArsError("duplicate registered code roots")
    for code_root in resolved_codes:
        if final_root == code_root or code_root in final_root.parents or final_root in code_root.parents:
            raise ArsError("control root must be disjoint from every code root")
    resolved_schema_root = Path(os.path.abspath(canonical_schema_root)) if canonical_schema_root is not None else None
    bootstrap_schemas, selected_schema_root = _authority_schema_registry(
        resolved_codes,
        resolved_schema_root,
        allow_bundled_fallback=final_root.exists(),
    )
    require_schema_binding = canonical_schema_root is not None
    if final_root.exists():
        return _verify_complete_store(
            final_root,
            final_root,
            project_id,
            value,
            resolved_codes,
            bootstrap_schemas,
            selected_schema_root,
            require_schema_binding=require_schema_binding,
        )
    resumed = _matching_complete_stage(
        final_root,
        project_id,
        value,
        bootstrap_hash,
        resolved_codes,
        bootstrap_schemas,
        selected_schema_root,
        require_schema_binding=require_schema_binding,
    )
    if resumed is None:
        if selected_schema_root is None:
            raise ArsError("new authority store requires a registered schema root")
        stage = final_root.with_name(f".{final_root.name}.authority-stage-{bootstrap_hash[:12]}-{secrets.token_hex(4)}")
        stage.mkdir()
        for name in (
            "objects",
            "events",
            "manifests",
            "receipts",
            "snapshots",
            "runtime",
        ):
            (stage / name).mkdir()
        _write_stage_marker(stage, bootstrap_hash, "building")
        _bootstrap_failpoint("after-stage-marker")
        identity = _write_identity(
            stage,
            final_root,
            resolved_codes,
            project_id,
            bootstrap_hash,
            selected_schema_root,
        )
        _bootstrap_failpoint("after-identity")
        _write_durable(
            stage / "manifests" / "authority-bootstrap.json",
            canonical_bytes(value),
            exclusive=True,
        )
        _bootstrap_failpoint("after-bootstrap")
        objects = ObjectStore(stage)
        objects.write("authority_grant", root.authority_grant_id, 1, value["root_grant"])
        _bootstrap_failpoint("after-root-object")
        objects.write(
            "authority_grant",
            publication.authority_grant_id,
            1,
            value["publication_grant"],
        )
        _bootstrap_failpoint("after-publication-object")
        command_id = new_id("command")
        idempotency_key = f"authority-bootstrap:{bootstrap_hash}"
        bootstrap_command = {
            "command_id": command_id,
            "command_type": "InitializeAuthorityRoot",
            "schema_id": "ars://core/command",
            "schema_version": "1.0.0",
            "submitted_at": value["root_grant"]["effective_at"],
            "actor_id": root.actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": root.authority_grant_id,
            "target_stream_id": root.authority_grant_id,
            "expected_stream_version": 0,
            "idempotency_key": idempotency_key,
            "correlation_id": idempotency_key,
            "causation_id": None,
            "reason": "initialize the approved authority root",
            "evidence_refs": [],
            "payload": value,
        }
        command_schema = bootstrap_schemas.validate(
            "ars://core/command",
            bootstrap_command,
            schema_version="1.0.0",
        )
        common = {
            "command_id": bootstrap_command["command_id"],
            "command_type": bootstrap_command["command_type"],
            "command_schema_id": command_schema.schema_id,
            "command_schema_version": command_schema.schema_version,
            "command_schema_sha256": command_schema.sha256,
            "actor_id": bootstrap_command["actor_id"],
            "authority_grant_id": bootstrap_command["authority_grant_id"],
            "idempotency_key": bootstrap_command["idempotency_key"],
            "command_payload_hash": bootstrap_hash,
            "correlation_id": bootstrap_command["correlation_id"],
            "causation_id": bootstrap_command["causation_id"],
            "schema_version": "1.0.0",
            "occurred_at": None,
        }
        ledger = EventLedger(stage, project_id, bootstrap_schemas)
        ledger.append(
            [
                {
                    **common,
                    "event_type": "AuthorityRootInitialized",
                    "stream_id": root.authority_grant_id,
                    "schema_id": "ars://core/event/AuthorityRootInitialized",
                    "payload": {
                        "bootstrap_manifest_sha256": bootstrap_hash,
                        "authorizing_grant_id": root.authority_grant_id,
                        "authorizing_grant_sha256": root.canonical_sha256,
                        "activated_grant_id": root.authority_grant_id,
                        "activated_grant_sha256": root.canonical_sha256,
                    },
                },
                {
                    **common,
                    "event_type": "AuthorityGrantActivated",
                    "stream_id": publication.authority_grant_id,
                    "schema_id": "ars://core/event/AuthorityGrantActivated",
                    "payload": {
                        "authorizing_grant_id": root.authority_grant_id,
                        "authorizing_grant_sha256": root.canonical_sha256,
                        "activated_grant_id": publication.authority_grant_id,
                        "activated_grant_sha256": publication.canonical_sha256,
                    },
                },
            ]
        )
        _bootstrap_failpoint("after-event-batch")
        _write_stage_marker(stage, bootstrap_hash, "complete")
        _flush_tree(stage)
        _verify_complete_store(
            stage,
            final_root,
            project_id,
            value,
            resolved_codes,
            bootstrap_schemas,
            selected_schema_root,
            require_schema_binding=require_schema_binding,
            require_genesis_only=True,
        )
    else:
        stage, identity = resumed
        _flush_tree(stage)
    _bootstrap_failpoint("after-staged-replay")
    try:
        os.rename(stage, final_root)
    except OSError as publish_error:
        collision = publish_error.errno in {errno.EEXIST, errno.ENOTEMPTY}
        if not collision and not final_root.exists():
            raise
        try:
            winner_identity = _verify_complete_store(
                final_root,
                final_root,
                project_id,
                value,
                resolved_codes,
                bootstrap_schemas,
                selected_schema_root,
                require_schema_binding=require_schema_binding,
            )
        except (ArsError, OSError) as verify_error:
            raise ConflictError("competing authority initializer published a foreign store") from verify_error
        _remove_stage_marker(final_root)
        _fsync_directory(final_root.parent)
        return winner_identity
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    _remove_stage_marker(final_root)
    _bootstrap_failpoint("after-rename")
    _fsync_directory(final_root.parent)
    return identity


class LedgerAuthorityGrantResolver:
    """Resolve authority exclusively from a bound store and verified replay.

    Args:
        control_root: Canonical authority-aware control-store root.
        project_id: Project identity bound into that store.
        expected_store_identity: Validated store identity from ControlBinding.
        schema_registry: Trusted registry used for mandatory ledger replay.

    Raises:
        ValueError: If ``project_id`` is malformed.
    """

    def __init__(
        self,
        control_root: Path,
        project_id: str,
        expected_store_identity: str,
        schema_registry: SchemaRegistry,
    ) -> None:
        self.control_root = control_root
        self.project_id = validate_id(project_id, "project")
        self.expected_store_identity = expected_store_identity
        if not isinstance(schema_registry, SchemaRegistry):
            raise TypeError("authority resolver requires a trusted SchemaRegistry")
        self.schema_registry = schema_registry

    def _projection(self) -> dict[str, Any]:
        from research_system.projection.replay import replay
        from research_system.store.identity import load_store_manifest, verify_store_identity
        from research_system.store.ledger import EventLedger

        try:
            verify_store_identity(self.control_root, self.project_id, self.expected_store_identity)
        except (OSError, IntegrityError) as exc:
            raise ArsError("authority_bootstrap_required") from exc
        manifest = load_store_manifest(self.control_root)
        if manifest.get("schema_version") != "1.1.0":
            raise ArsError("authority_bootstrap_required")
        bootstrap_path = self.control_root / "manifests" / "authority-bootstrap.json"
        try:
            bootstrap_bytes = bootstrap_path.read_bytes()
            bootstrap = json.loads(bootstrap_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityError("authority bootstrap manifest invalid") from exc
        if bootstrap_bytes != canonical_bytes(bootstrap):
            raise IntegrityError("authority bootstrap manifest is not canonical")
        bootstrap_hash = authority_bootstrap_sha256(bootstrap)
        if bootstrap_hash != manifest.get("bootstrap_manifest_sha256"):
            raise IntegrityError("authority bootstrap identity binding mismatch")
        events = tuple(
            EventLedger(
                self.control_root,
                self.project_id,
                self.schema_registry,
            ).iter_events()
        )
        projection = replay(events, schema_registry=self.schema_registry)
        if projection.get("bootstrap_manifest_sha256") != bootstrap_hash:
            raise IntegrityError("authority bootstrap ledger binding mismatch")
        _verify_bootstrap_bindings(
            self.control_root,
            self.project_id,
            bootstrap,
            events,
            projection,
        )
        return projection

    def _load_grant(self, grant_id: str, projection: dict[str, Any]) -> tuple[AuthorityGrant, dict[str, Any]]:
        record = projection.get("authority_grants", {}).get(grant_id)
        if record is None:
            raise ArsError("authority grant is not activated")
        directory = self.control_root / "objects" / "authority_grant" / grant_id
        matches = sorted(directory.glob("00000001-*.json"))
        if len(matches) != 1:
            raise IntegrityError("authority grant object missing or duplicated")
        try:
            value = json.loads(matches[0].read_text(encoding="utf-8"))
            grant = AuthorityGrant.from_dict(value)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise IntegrityError("authority grant object invalid") from exc
        if (
            grant.authority_grant_id != grant_id
            or grant.canonical_sha256 != record["authority_grant_sha256"]
            or not matches[0].name.endswith(f"-{grant.canonical_sha256}.json")
        ):
            raise IntegrityError("authority grant object hash mismatch")
        return grant, record

    def _resolution_from_projection(
        self,
        grant_id: str,
        projection: dict[str, Any],
    ) -> tuple[AuthorityGrantResolution, AuthorityGrant, dict[str, Any]]:
        grant, record = self._load_grant(grant_id, projection)
        result = AuthorityGrantResolution(
            authority_grant_id=grant_id,
            authority_grant_sha256=grant.canonical_sha256,
            actor_id=grant.actor_id,
            subject_scope=grant.subject_scope,
            effective_at=grant.effective_at,
            expires_at=grant.expires_at,
            activation_event_id=record["activation_event_id"],
            activation_position=record["activation_position"],
            status=record["status"],
            revocation_event_id=record.get("revocation_event_id"),
        )
        return result, grant, record

    @staticmethod
    def _validate_current_grant(
        grant: AuthorityGrant,
        record: dict[str, Any],
        now: datetime,
    ) -> None:
        if now.tzinfo != UTC:
            raise ValueError("trusted authority time must be UTC")
        if record["status"] == "revoked":
            raise ArsError("authority grant revoked")
        if now < grant.effective_at:
            raise ArsError("authority grant not effective")
        if grant.expires_at is not None and now >= grant.expires_at:
            raise ArsError("authority grant expired")

    def grant_at(self, grant_id: str, now: datetime) -> AuthorityGrantResolution:
        """Resolve a currently active grant at a trusted UTC time.

        Args:
            grant_id: Activated authority grant identity.
            now: Trusted local operator time in UTC.

        Returns:
            Replay-derived immutable grant evidence.

        Raises:
            ValueError: If ``now`` is not UTC.
            ArsError: If the grant is unavailable, inactive, or out of time.
            IntegrityError: If canonical store evidence is invalid.
        """
        projection = self._projection()
        result, grant, record = self._resolution_from_projection(grant_id, projection)
        self._validate_current_grant(grant, record, now)
        return result

    def grant_identity(self, grant_id: str) -> AuthorityGrantResolution:
        """Resolve immutable grant identity without asserting current usability.

        Args:
            grant_id: Activated authority grant identity.

        Returns:
            Replay-derived grant identity, hash, scope, and current status.

        Raises:
            ArsError: If the grant has no canonical activation history.
            IntegrityError: If canonical store evidence is invalid.
        """
        projection = self._projection()
        result, _, _ = self._resolution_from_projection(grant_id, projection)
        return result

    def resolve(
        self,
        grant_id: str,
        actor_id: str,
        command_type: str,
        project_id: str,
        subject_kind: str,
        subject_id: str,
        now: datetime,
    ) -> AuthorityGrantResolution:
        """Resolve a grant and enforce its exact actor, command, and subject scope.

        Args:
            grant_id: Activated authority grant identity.
            actor_id: Attributed command actor identity.
            command_type: Exact command type being authorized.
            project_id: Project identity of the governed target.
            subject_kind: Registered governed subject kind.
            subject_id: Exact governed subject identity.
            now: Trusted local operator time in UTC.

        Returns:
            Replay-derived immutable grant evidence.

        Raises:
            ArsError: If any authority constraint is not satisfied.
            IntegrityError: If canonical store evidence is invalid.
            ValueError: If an identity or trusted time is malformed.
        """
        projection = self._projection()
        result, grant, record = self._resolution_from_projection(grant_id, projection)
        self._validate_current_grant(grant, record, now)
        if result.actor_id != actor_id:
            raise ArsError("authority actor mismatch")
        if command_type not in grant.allowed_command_types:
            raise ArsError("authority command mismatch")
        if result.subject_scope != AuthorityScope(project_id, subject_kind, subject_id):
            raise ArsError("authority subject scope mismatch")
        return result
