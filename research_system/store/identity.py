from __future__ import annotations

import json
import errno
import os
import secrets
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.layout import (
    require_control_root_disjoint_from_code_roots,
    require_external_control_root,
)

_IDENTITY_NAME = "store-identity.json"
_SCHEMA_SUFFIX = Path(".research-system") / "schemas"
SCHEMA_BINDING_VERSION = "1.0.0"


def _manifest_path(control_root: Path) -> Path:
    return control_root / "manifests" / _IDENTITY_NAME


def _manifest_hash(manifest: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    return sha256_hex(canonical_bytes(unsigned))


def _read_manifest(path: Path, *, require_canonical: bool) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"invalid store identity manifest: {path}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"invalid store identity manifest: {path}")
    if require_canonical and raw != canonical_bytes(value):
        raise IntegrityError("store identity manifest is noncanonical")
    if value.get("manifest_hash") != _manifest_hash(value):
        raise IntegrityError("store identity manifest hash mismatch")
    return value


def _validate_manifest_identity(manifest: dict[str, Any]) -> None:
    control_root = manifest.get("control_root")
    if not isinstance(control_root, str) or not Path(control_root).is_absolute():
        raise IntegrityError("invalid store control-root binding")
    validate_id(str(manifest.get("project_id")), "project")
    identity = manifest.get("store_identity")
    if not isinstance(identity, str) or len(identity) != 64:
        raise IntegrityError("invalid store identity")
    try:
        int(identity, 16)
    except ValueError as exc:
        raise IntegrityError("invalid store identity") from exc
    version = manifest.get("schema_version")
    if version not in {"1.0.0", "1.1.0"}:
        raise IntegrityError("unsupported store identity version")
    if version == "1.1.0":
        stable = {
            "schema_id": manifest.get("schema_id"),
            "schema_version": version,
            "store_nonce": manifest.get("store_nonce"),
            "project_id": manifest.get("project_id"),
            "bootstrap_manifest_sha256": manifest.get("bootstrap_manifest_sha256"),
        }
        if identity != sha256_hex(canonical_bytes(stable)):
            raise IntegrityError("derived store identity mismatch")
        manifest_schema_root(manifest)


def load_store_manifest_unbound(control_root: Path) -> dict[str, Any]:
    """Load a source-bound manifest for the explicit restore finalization path.

    This is intentionally not a relocation-tolerant variant of
    :func:`load_store_manifest`; callers must use the restore authority seam and
    rebind the manifest before normal store loading.
    """
    control = control_root.resolve(strict=True)
    manifest = _read_manifest(_manifest_path(control), require_canonical=True)
    _validate_manifest_identity(manifest)
    return manifest


def manifest_schema_root(manifest: dict[str, Any]) -> Path | None:
    """Return a structurally verified canonical schema binding, if persisted.

    Args:
        manifest: Loaded store-identity manifest.

    Returns:
        The registered canonical schema path, or ``None`` for a legacy manifest.

    Raises:
        IntegrityError: If schema-binding metadata is malformed or unregistered.
    """
    binding_version = manifest.get("schema_binding_version")
    if binding_version is not None and binding_version != SCHEMA_BINDING_VERSION:
        raise IntegrityError("invalid store schema-root binding version")
    value = manifest.get("schema_root")
    if value is None:
        if binding_version is not None:
            raise IntegrityError("store schema-root binding missing")
        return None
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise IntegrityError("invalid store schema-root binding")
    roots = manifest.get("code_roots")
    if (
        not isinstance(roots, list)
        or not roots
        or any(not isinstance(root, str) or not Path(root).is_absolute() for root in roots)
    ):
        raise IntegrityError("invalid store code-root binding")
    expected = {str(Path(root) / _SCHEMA_SUFFIX) for root in roots}
    if value not in expected:
        raise IntegrityError("store schema root is not registered")
    return Path(value)


def initialize_control_store(
    code_roots: list[Path],
    control_root: Path,
    project_id: str,
) -> str:
    project_id = validate_id(project_id, "project")
    control = require_external_control_root(code_roots, control_root)
    manifest_path = _manifest_path(control)
    if manifest_path.exists():
        raise ConflictError(f"control store already initialized: {control}")
    resolved_codes = sorted(str(root.resolve(strict=True)) for root in code_roots)
    manifest: dict[str, Any] = {
        "schema_id": "ars://core/store-identity",
        "schema_version": "1.0.0",
        "project_id": project_id,
        "store_identity": secrets.token_hex(32),
        "control_root": str(control),
        "code_roots": resolved_codes,
        "endpoint_scheme": "local-cli",
    }
    manifest["manifest_hash"] = _manifest_hash(manifest)
    try:
        fd = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ConflictError(f"control store already initialized: {control}") from exc
    with os.fdopen(fd, "wb") as handle:
        handle.write(canonical_bytes(manifest))
        handle.flush()
        os.fsync(handle.fileno())
    return str(manifest["store_identity"])


def load_store_manifest(control_root: Path) -> dict[str, Any]:
    control = control_root.resolve(strict=True)
    manifest = _read_manifest(_manifest_path(control), require_canonical=False)
    if manifest.get("control_root") != str(control):
        raise IntegrityError("store control-root binding mismatch")
    _validate_manifest_identity(manifest)
    return manifest


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
    finally:
        os.close(descriptor)


def rebind_restored_store(
    target_root: Path,
    source_root: Path,
    *,
    expected_project_id: str | None = None,
    expected_store_identity: str | None = None,
    expected_code_roots: list[Path] | None = None,
    expected_schema_root: Path | None = None,
) -> dict[str, Any]:
    """Atomically bind one verified restored store to its target root.

    The only mutable manifest fields are ``control_root`` and its
    ``manifest_hash``.  A manifest already bound to ``target_root`` is an exact
    idempotent retry; any identity or root-binding disagreement is a conflict.
    """
    target = target_root.resolve(strict=True)
    source = source_root.resolve(strict=False)
    if source == target:
        raise ConflictError("restored store source must differ from target")

    manifest_path = _manifest_path(target)
    manifest = load_store_manifest_unbound(target)
    current_value = manifest.get("control_root")
    if not isinstance(current_value, str):
        raise IntegrityError("invalid store control-root binding")
    current = Path(current_value).resolve(strict=False)
    if current != source and current != target:
        raise ConflictError("restored store source binding mismatch")

    if expected_project_id is not None and manifest.get("project_id") != expected_project_id:
        raise ConflictError("project identity mismatch")
    if expected_store_identity is not None and manifest.get("store_identity") != expected_store_identity:
        raise ConflictError("store identity mismatch")

    code_values = manifest.get("code_roots")
    if (
        not isinstance(code_values, list)
        or not code_values
        or any(not isinstance(value, str) or not Path(value).is_absolute() for value in code_values)
    ):
        raise IntegrityError("invalid store code-root binding")
    code_roots = [Path(value) for value in code_values]
    if expected_code_roots is not None:
        expected_codes = sorted(str(root.resolve(strict=True)) for root in expected_code_roots)
        if code_values != expected_codes:
            raise ConflictError("code root binding mismatch")
    require_control_root_disjoint_from_code_roots(code_roots, target)

    persisted_schema_root = manifest_schema_root(manifest)
    if expected_schema_root is not None:
        if persisted_schema_root is None or persisted_schema_root.resolve(strict=False) != expected_schema_root.resolve(
            strict=False
        ):
            raise ConflictError("schema root binding mismatch")

    if current == target:
        return manifest

    rebound = dict(manifest)
    rebound["control_root"] = str(target)
    rebound["manifest_hash"] = _manifest_hash(rebound)
    if set(rebound).difference({"control_root", "manifest_hash"}) != set(manifest).difference(
        {"control_root", "manifest_hash"}
    ):
        raise IntegrityError("restore rebind changed manifest fields")
    data = canonical_bytes(rebound)
    temporary = manifest_path.with_name(f".{manifest_path.name}.{secrets.token_hex(16)}.tmp")
    descriptor = -1
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, manifest_path)
        _fsync_directory(manifest_path.parent)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return rebound


def verify_store_identity(
    control_root: Path,
    expected_project_id: str,
    expected_store_identity: str,
    expected_code_roots: list[Path] | None = None,
) -> str:
    manifest = load_store_manifest(control_root)
    if manifest["project_id"] != expected_project_id:
        raise ArsError("store project identity mismatch")
    if manifest["store_identity"] != expected_store_identity:
        raise ArsError("store identity mismatch")
    if expected_code_roots is not None:
        resolved = sorted(str(root.resolve(strict=True)) for root in expected_code_roots)
        if manifest.get("code_roots") != resolved:
            raise ArsError("code root binding mismatch")
    return str(manifest["store_identity"])
