from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.layout import require_external_control_root

_IDENTITY_NAME = 'store-identity.json'


def _manifest_path(control_root: Path) -> Path:
    return control_root / 'manifests' / _IDENTITY_NAME


def _manifest_hash(manifest: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != 'manifest_hash'}
    return sha256_hex(canonical_bytes(unsigned))


def initialize_control_store(
    code_roots: list[Path],
    control_root: Path,
    project_id: str,
) -> str:
    project_id = validate_id(project_id, 'project')
    control = require_external_control_root(code_roots, control_root)
    manifest_path = _manifest_path(control)
    if manifest_path.exists():
        raise ConflictError(f'control store already initialized: {control}')
    resolved_codes = sorted(str(root.resolve(strict=True)) for root in code_roots)
    manifest: dict[str, Any] = {
        'schema_id': 'ars://core/store-identity',
        'schema_version': '1.0.0',
        'project_id': project_id,
        'store_identity': secrets.token_hex(32),
        'control_root': str(control),
        'code_roots': resolved_codes,
        'endpoint_scheme': 'local-cli',
    }
    manifest['manifest_hash'] = _manifest_hash(manifest)
    try:
        fd = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ConflictError(f'control store already initialized: {control}') from exc
    with os.fdopen(fd, 'wb') as handle:
        handle.write(canonical_bytes(manifest))
        handle.flush()
        os.fsync(handle.fileno())
    return str(manifest['store_identity'])


def load_store_manifest(control_root: Path) -> dict[str, Any]:
    control = control_root.resolve(strict=True)
    path = _manifest_path(control)
    try:
        manifest = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f'invalid store identity manifest: {path}') from exc
    if manifest.get('manifest_hash') != _manifest_hash(manifest):
        raise IntegrityError('store identity manifest hash mismatch')
    if manifest.get('control_root') != str(control):
        raise IntegrityError('store control-root binding mismatch')
    validate_id(str(manifest.get('project_id')), 'project')
    identity = manifest.get('store_identity')
    if not isinstance(identity, str) or len(identity) != 64:
        raise IntegrityError('invalid store identity')
    try:
        int(identity, 16)
    except ValueError as exc:
        raise IntegrityError('invalid store identity') from exc
    return manifest


def verify_store_identity(
    control_root: Path,
    expected_project_id: str,
    expected_store_identity: str,
    expected_code_roots: list[Path] | None = None,
) -> str:
    manifest = load_store_manifest(control_root)
    if manifest['project_id'] != expected_project_id:
        raise ArsError('store project identity mismatch')
    if manifest['store_identity'] != expected_store_identity:
        raise ArsError('store identity mismatch')
    if expected_code_roots is not None:
        resolved = sorted(
            str(root.resolve(strict=True)) for root in expected_code_roots
        )
        if manifest['code_roots'] != resolved:
            raise ArsError('code root binding mismatch')
    return str(manifest['store_identity'])
