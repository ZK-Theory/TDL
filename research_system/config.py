from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.errors import ConfigurationError
from research_system.ids import validate_id
from research_system.store.identity import verify_store_identity
from research_system.store.layout import require_external_control_root


@dataclass(frozen=True)
class ControlBinding:
    code_roots: tuple[Path, ...]
    control_root: Path
    project_id: str
    schema_root: Path
    store_identity: str

    @classmethod
    def load(cls, path: Path) -> 'ControlBinding':
        try:
            value: Any = yaml.safe_load(path.read_text(encoding='utf-8'))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f'invalid binding config: {path}') from exc
        if not isinstance(value, dict):
            raise ConfigurationError('binding config must be an object')
        required = {
            'code_roots',
            'control_root',
            'project_id',
            'schema_root',
            'store_identity',
        }
        missing = sorted(required.difference(value))
        if missing:
            raise ConfigurationError(f'missing binding fields: {", ".join(missing)}')
        roots_value = value['code_roots']
        if not isinstance(roots_value, list) or not roots_value:
            raise ConfigurationError('code_roots must be a non-empty list')
        code_roots = tuple(Path(item) for item in roots_value)
        control_root = Path(value['control_root'])
        schema_root = Path(value['schema_root'])
        all_paths = (*code_roots, control_root, schema_root)
        if any(not item.is_absolute() for item in all_paths):
            raise ConfigurationError('all binding paths must be absolute')
        project_id = validate_id(str(value['project_id']), 'project')
        control_root = require_external_control_root(list(code_roots), control_root)
        verify_store_identity(
            control_root,
            project_id,
            str(value['store_identity']),
            list(code_roots),
        )
        if not schema_root.resolve(strict=True).is_dir():
            raise ConfigurationError('schema_root must be an existing directory')
        return cls(
            tuple(root.resolve(strict=True) for root in code_roots),
            control_root,
            project_id,
            schema_root.resolve(strict=True),
            str(value['store_identity']),
        )
