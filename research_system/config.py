from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConfigurationError
from research_system.ids import validate_id
from research_system.store.identity import (
    load_store_manifest,
    manifest_schema_root,
    verify_store_identity,
)
from research_system.store.layout import (
    require_existing_control_root,
)


_FOUNDATION_REQUIRED_FIELDS = frozenset(
    {
        "project_id",
        "control_root",
        "store_identity",
        "endpoint_scheme",
        "canonical_uri",
        "canonical_tail_position",
        "canonical_tail_hash",
        "code_roots",
        "schema_root",
        "foundation_sha256",
    }
)
_FOUNDATION_PLACEHOLDERS = frozenset({"", "null", "none", "placeholder", "todo", "tbd", "unknown"})


def _foundation_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip().lower() in _FOUNDATION_PLACEHOLDERS:
        raise ConfigurationError(f"approved {field} must be a materialized value")
    return value


def _foundation_sha256(value: dict[str, Any]) -> str:
    return sha256_hex(canonical_bytes({key: item for key, item in value.items() if key != "foundation_sha256"}))


def _foundation_digest(value: Any, field: str) -> str:
    digest = _foundation_string(value, field)
    if len(digest) != 64 or digest.lower() != digest:
        raise ConfigurationError(f"approved {field} must be a lowercase SHA-256 digest")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise ConfigurationError(f"approved {field} must be a lowercase SHA-256 digest") from exc
    return digest


@dataclass(frozen=True)
class ApprovedProjectBinding:
    """Owner-approved authority for one restore transaction.

    This record is deliberately independent of the source and target manifests.
    Loading it also requires the currently materialized external store to match
    the recorded identity; historical values alone are never operational.
    """

    project_id: str
    control_root: Path
    store_identity: str
    endpoint_scheme: str
    canonical_uri: str
    canonical_tail_position: int
    canonical_tail_hash: str
    code_roots: tuple[Path, ...]
    schema_root: Path
    foundation_sha256: str

    @classmethod
    def load(cls, path: Path) -> "ApprovedProjectBinding":
        try:
            value: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"invalid approved project binding: {path}") from exc
        if not isinstance(value, dict):
            raise ConfigurationError("approved project binding must be an object")
        missing = sorted(_FOUNDATION_REQUIRED_FIELDS.difference(value))
        if missing:
            raise ConfigurationError(f"missing approved project binding fields: {', '.join(missing)}")
        if value.get("schema_version") != "1.0.0":
            raise ConfigurationError("unsupported approved project binding schema version")
        if value.get("control_root_required") is not True:
            raise ConfigurationError("approved control_root_required must be true")
        if value.get("canonical_hash") != "sha256":
            raise ConfigurationError("approved canonical_hash must be sha256")
        project_id = validate_id(_foundation_string(value["project_id"], "project_id"), "project")
        store_identity = _foundation_digest(value["store_identity"], "store_identity")
        endpoint_scheme = _foundation_string(value["endpoint_scheme"], "endpoint_scheme")
        canonical_uri = _foundation_string(value["canonical_uri"], "canonical_uri")
        if not canonical_uri.startswith(f"{endpoint_scheme}://") or canonical_uri == f"{endpoint_scheme}://":
            raise ConfigurationError("approved canonical_uri must be a concrete endpoint")
        tail_position = value["canonical_tail_position"]
        if isinstance(tail_position, bool) or not isinstance(tail_position, int) or tail_position < 0:
            raise ConfigurationError("approved canonical_tail_position must be a non-negative integer")
        tail_hash = _foundation_digest(value["canonical_tail_hash"], "canonical_tail_hash")
        roots_value = value["code_roots"]
        if not isinstance(roots_value, list) or not roots_value:
            raise ConfigurationError("approved code_roots must be a non-empty list")
        if any(not isinstance(item, str) for item in roots_value):
            raise ConfigurationError("approved code_roots must contain strings")
        code_roots = tuple(Path(item) for item in roots_value)
        control_root = Path(_foundation_string(value["control_root"], "control_root"))
        if not isinstance(value["schema_root"], str):
            raise ConfigurationError("approved schema_root must be a materialized string")
        schema_root = Path(value["schema_root"])
        all_paths = (*code_roots, control_root, schema_root)
        if any(not path_value.is_absolute() for path_value in all_paths):
            raise ConfigurationError("approved project binding paths must be absolute")
        try:
            resolved_code_roots = tuple(sorted((root.resolve(strict=True) for root in code_roots), key=str))
            resolved_control_root = control_root.resolve(strict=True)
            resolved_schema_root = schema_root.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise ConfigurationError("approved project binding path is unavailable") from exc
        if not resolved_control_root.is_dir():
            raise ConfigurationError("approved control_root must be an existing directory")
        if not resolved_schema_root.is_dir():
            raise ConfigurationError("approved schema_root must be an existing directory")
        if len(set(resolved_code_roots)) != len(resolved_code_roots):
            raise ConfigurationError("approved code_roots must be unique")
        if resolved_schema_root not in {root / ".research-system" / "schemas" for root in resolved_code_roots}:
            raise ConfigurationError("approved schema_root is not registered by an approved code root")
        try:
            require_existing_control_root(list(resolved_code_roots), resolved_control_root)
            manifest = load_store_manifest(resolved_control_root)
        except (ArsError, OSError, ValueError) as exc:
            raise ConfigurationError("approved control_root has no matching materialized store") from exc
        if manifest.get("project_id") != project_id or manifest.get("store_identity") != store_identity:
            raise ConfigurationError("materialized store identity differs from approved project binding")
        if manifest.get("code_roots") != [str(root) for root in resolved_code_roots]:
            raise ConfigurationError("materialized store code roots differ from approved project binding")
        persisted_schema_root = manifest_schema_root(manifest)
        if persisted_schema_root is None or persisted_schema_root.resolve(strict=True) != resolved_schema_root:
            raise ConfigurationError("materialized store schema root differs from approved project binding")
        if manifest.get("endpoint_scheme") != endpoint_scheme:
            raise ConfigurationError("materialized store endpoint differs from approved project binding")
        foundation_sha256 = _foundation_digest(value["foundation_sha256"], "foundation_sha256")
        if foundation_sha256 != _foundation_sha256(value):
            raise ConfigurationError("approved project binding foundation digest mismatch")
        return cls(
            project_id,
            resolved_control_root,
            store_identity,
            endpoint_scheme,
            canonical_uri,
            tail_position,
            tail_hash,
            resolved_code_roots,
            resolved_schema_root,
            foundation_sha256,
        )


@dataclass(frozen=True)
class ControlBinding:
    code_roots: tuple[Path, ...]
    control_root: Path
    project_id: str
    schema_root: Path
    store_identity: str

    @classmethod
    def load(cls, path: Path) -> "ControlBinding":
        try:
            value: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"invalid binding config: {path}") from exc
        if not isinstance(value, dict):
            raise ConfigurationError("binding config must be an object")
        required = {
            "code_roots",
            "control_root",
            "project_id",
            "schema_root",
            "store_identity",
        }
        missing = sorted(required.difference(value))
        if missing:
            raise ConfigurationError(f"missing binding fields: {', '.join(missing)}")
        roots_value = value["code_roots"]
        if not isinstance(roots_value, list) or not roots_value:
            raise ConfigurationError("code_roots must be a non-empty list")
        code_roots = tuple(Path(item) for item in roots_value)
        control_root = Path(value["control_root"])
        schema_root = Path(value["schema_root"])
        all_paths = (*code_roots, control_root, schema_root)
        if any(not item.is_absolute() for item in all_paths):
            raise ConfigurationError("all binding paths must be absolute")
        project_id = validate_id(str(value["project_id"]), "project")
        control_root = require_existing_control_root(list(code_roots), control_root)
        verify_store_identity(
            control_root,
            project_id,
            str(value["store_identity"]),
            list(code_roots),
        )
        try:
            resolved_schema_root = schema_root.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ConfigurationError("configured schema root is unavailable") from exc
        if not resolved_schema_root.is_dir():
            raise ConfigurationError("schema_root must be an existing directory")
        persisted_schema_root = manifest_schema_root(load_store_manifest(control_root))
        if persisted_schema_root is not None:
            try:
                resolved_persisted_schema_root = persisted_schema_root.resolve(strict=True)
            except FileNotFoundError as exc:
                raise ConfigurationError("store manifest schema root is missing") from exc
            if resolved_schema_root != resolved_persisted_schema_root:
                raise ConfigurationError("schema_root conflicts with store manifest")
        return cls(
            tuple(root.resolve(strict=True) for root in code_roots),
            control_root,
            project_id,
            resolved_schema_root,
            str(value["store_identity"]),
        )
