from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.errors import ConfigurationError
from research_system.ids import validate_id
from research_system.store.identity import (
    load_store_manifest,
    manifest_schema_root,
    verify_store_identity,
)
from research_system.store.layout import require_external_control_root


@dataclass(frozen=True)
class ApprovedProjectBinding:
    """Independently supplied project and schema roots for restore binding."""

    project_id: str
    code_roots: tuple[Path, ...]
    schema_root: Path

    @classmethod
    def load(cls, path: Path) -> "ApprovedProjectBinding":
        try:
            value: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"invalid approved project binding: {path}") from exc
        if not isinstance(value, dict):
            raise ConfigurationError("approved project binding must be an object")
        required = {"project_id", "code_roots", "schema_root"}
        missing = sorted(required.difference(value))
        if missing:
            raise ConfigurationError(f"missing approved project binding fields: {', '.join(missing)}")
        if not isinstance(value["project_id"], str):
            raise ConfigurationError("approved project_id must be a string")
        project_id = validate_id(value["project_id"], "project")
        roots_value = value["code_roots"]
        if not isinstance(roots_value, list) or not roots_value:
            raise ConfigurationError("approved code_roots must be a non-empty list")
        if any(not isinstance(item, str) for item in roots_value):
            raise ConfigurationError("approved code_roots must contain strings")
        code_roots = tuple(Path(item) for item in roots_value)
        if not isinstance(value["schema_root"], str):
            raise ConfigurationError("approved schema_root must be a string")
        schema_root = Path(value["schema_root"])
        all_paths = (*code_roots, schema_root)
        if any(not path_value.is_absolute() for path_value in all_paths):
            raise ConfigurationError("approved project binding paths must be absolute")
        try:
            resolved_code_roots = tuple(sorted((root.resolve(strict=True) for root in code_roots), key=str))
            resolved_schema_root = schema_root.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise ConfigurationError("approved project binding path is unavailable") from exc
        if not resolved_schema_root.is_dir():
            raise ConfigurationError("approved schema_root must be an existing directory")
        if len(set(resolved_code_roots)) != len(resolved_code_roots):
            raise ConfigurationError("approved code_roots must be unique")
        if resolved_schema_root not in {root / ".research-system" / "schemas" for root in resolved_code_roots}:
            raise ConfigurationError("approved schema_root is not registered by an approved code root")
        return cls(project_id, resolved_code_roots, resolved_schema_root)


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
        control_root = require_external_control_root(list(code_roots), control_root)
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
