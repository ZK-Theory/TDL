from __future__ import annotations

import json
import errno
import os
import secrets
from pathlib import Path
from typing import Any, Callable

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.layout import (
    require_control_root_disjoint_from_code_roots,
    require_external_control_root,
)

_IDENTITY_NAME = "store-identity.json"
_RESTORE_BINDING_EVIDENCE_NAME = "restore-binding-evidence.json"
_RESTORE_BINDING_PENDING_NAME = ".restore-binding-evidence.pending"
_RESTORE_OPERATION_STATUSES = frozenset({"unbound", "bound-and-config-published", "bound-but-config-unpublished"})
_RESTORE_DURABILITY_STATUSES = frozenset({"durable", "pending"})
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


def _fsync_directory(path: Path) -> bool:
    """Attempt directory-entry durability and report unsupported platforms honestly."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) == 5:
            return False
        if exc.errno in {errno.EACCES, errno.EINVAL, errno.ENOTSUP}:
            return False
        raise
    try:
        try:
            os.fsync(descriptor)
        except OSError as exc:
            if os.name == "nt" and getattr(exc, "winerror", None) in {1, 5, 87}:
                return False
            if exc.errno in {errno.EACCES, errno.EINVAL, errno.ENOTSUP}:
                return False
            raise
    finally:
        os.close(descriptor)
    return True


def _restore_binding_evidence_path(control_root: Path) -> Path:
    return control_root / "manifests" / _RESTORE_BINDING_EVIDENCE_NAME


def _restore_binding_pending_path(control_root: Path) -> Path:
    return control_root / "manifests" / _RESTORE_BINDING_PENDING_NAME


def _read_restore_binding_evidence(
    control_root: Path,
    *,
    include_pending: bool,
) -> tuple[dict[str, Any] | None, Path | None]:
    candidates = (
        [_restore_binding_pending_path(control_root), _restore_binding_evidence_path(control_root)]
        if include_pending
        else [_restore_binding_evidence_path(control_root)]
    )
    for path in candidates:
        if not path.exists():
            continue
        try:
            raw = path.read_bytes()
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("restore binding evidence is invalid") from exc
        if not isinstance(value, dict) or raw != canonical_bytes(value):
            raise IntegrityError("restore binding evidence is noncanonical")
        if set(value) != {
            "source_root",
            "target_root",
            "project_id",
            "store_identity",
            "manifest_hash",
            "receipt_hash",
            "source_snapshot",
            "source_snapshot_hash",
            "operation_status",
            "durability_status",
            "expected_output_bytes",
            "expected_output_sha256",
            "target_manifest_bytes_sha256",
        }:
            raise IntegrityError("restore binding evidence fields are invalid")
        snapshot = value["source_snapshot"]
        snapshot_hash = value["source_snapshot_hash"]
        expected_output = value["expected_output_bytes"]
        expected_output_hash = value["expected_output_sha256"]
        if (
            not isinstance(value["source_root"], str)
            or not Path(value["source_root"]).is_absolute()
            or not isinstance(value["target_root"], str)
            or not Path(value["target_root"]).is_absolute()
            or not isinstance(value["project_id"], str)
            or not isinstance(value["store_identity"], str)
            or not isinstance(value["manifest_hash"], str)
            or len(value["manifest_hash"]) != 64
            or not isinstance(value["receipt_hash"], str)
            or value["receipt_hash"]
            and len(value["receipt_hash"]) != 64
            or not isinstance(snapshot, dict)
            or not isinstance(snapshot_hash, str)
            or bool(snapshot)
            and (not snapshot_hash or snapshot_hash != sha256_hex(canonical_bytes(snapshot)))
            or not snapshot
            and snapshot_hash
            or not isinstance(value["operation_status"], str)
            or value["operation_status"] not in _RESTORE_OPERATION_STATUSES
            or not isinstance(value["durability_status"], str)
            or value["durability_status"] not in _RESTORE_DURABILITY_STATUSES
            or not isinstance(expected_output, str)
            or not isinstance(expected_output_hash, str)
            or expected_output_hash
            and expected_output_hash != sha256_hex(expected_output.encode("utf-8"))
            or not expected_output_hash
            and expected_output
            or not isinstance(value["target_manifest_bytes_sha256"], str)
            or len(value["target_manifest_bytes_sha256"]) != 64
        ):
            raise IntegrityError("restore binding evidence values are invalid")
        if Path(value["target_root"]).resolve(strict=False) != control_root.resolve(strict=False):
            raise IntegrityError("restore binding evidence target mismatch")
        if Path(value["source_root"]).resolve(strict=False) == control_root.resolve(strict=False):
            raise IntegrityError("restore binding evidence source overlaps target")
        return value, path
    return None, None


def load_restore_binding_evidence(control_root: Path) -> dict[str, Any] | None:
    """Load durable original-source evidence, including an interrupted pending publication."""
    control = control_root.resolve(strict=True)
    value, _ = _read_restore_binding_evidence(control, include_pending=True)
    return value


def _write_restore_binding_pending(
    control_root: Path,
    value: dict[str, Any],
    *,
    replace: bool = False,
) -> bool:
    pending = _restore_binding_pending_path(control_root)
    data = canonical_bytes(value)
    if pending.exists() and not replace:
        if pending.read_bytes() != data:
            raise ConflictError("restore binding evidence conflicts with a pending retry")
        return True
    if pending.exists() and replace and pending.read_bytes() == data:
        return True
    if replace:
        temporary = pending.with_name(f".{pending.name}.{secrets.token_hex(16)}.tmp")
        descriptor = -1
        try:
            descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = -1
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, pending)
            return _fsync_directory(pending.parent)
        finally:
            if descriptor != -1:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)
    descriptor = -1
    try:
        descriptor = os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        return _fsync_directory(pending.parent)
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _publish_restore_binding_pending(control_root: Path) -> bool:
    pending = _restore_binding_pending_path(control_root)
    if not pending.exists():
        raise IntegrityError("restore binding evidence is missing")
    os.replace(pending, _restore_binding_evidence_path(control_root))
    return _fsync_directory(pending.parent)


def _before_restore_manifest_replace() -> None:
    """Test seam immediately before the final source/target revalidation."""


def rebind_restored_store(
    target_root: Path,
    source_root: Path,
    *,
    expected_project_id: str | None = None,
    expected_store_identity: str | None = None,
    expected_code_roots: list[Path] | None = None,
    expected_schema_root: Path | None = None,
    expected_restore_receipt_hash: str | None = None,
    source_snapshot: dict[str, Any] | None = None,
    expected_source_snapshot_hash: str | None = None,
    expected_target_manifest_bytes_sha256: str | None = None,
    expected_output: bytes | None = None,
    source_snapshot_validator: Callable[[], None] | None = None,
    output_commit: Callable[[], Any] | None = None,
    output_rollback: Callable[[], None] | None = None,
    post_commit: Callable[[], Any] | None = None,
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
    original_manifest_bytes = manifest_path.read_bytes()
    original_manifest_bytes_sha256 = sha256_hex(original_manifest_bytes)
    if not _fsync_directory(manifest_path.parent):
        raise ArsError("restore binding requires durable manifest directory")
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
    if expected_code_roots is None:
        raise ArsError("approved code-root binding is required")

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
    if persisted_schema_root is not None and expected_schema_root is None:
        raise ArsError("approved schema-root binding is required")
    if expected_schema_root is not None:
        if persisted_schema_root is None or persisted_schema_root.resolve(strict=False) != expected_schema_root.resolve(
            strict=False
        ):
            raise ConflictError("schema root binding mismatch")

    evidence, evidence_path = _read_restore_binding_evidence(target, include_pending=True)
    if current == target:
        if evidence is None or evidence["source_root"] != str(source):
            raise ConflictError("restore source binding evidence mismatch")
        if evidence["project_id"] != manifest["project_id"] or evidence["store_identity"] != manifest["store_identity"]:
            raise IntegrityError("restore binding evidence identity mismatch")
        if evidence["manifest_hash"] != manifest["manifest_hash"]:
            raise IntegrityError("restore binding evidence manifest mismatch")
        if evidence["target_manifest_bytes_sha256"] != original_manifest_bytes_sha256:
            raise IntegrityError("restore binding evidence target manifest mismatch")
        if expected_restore_receipt_hash is not None and evidence["receipt_hash"] != expected_restore_receipt_hash:
            raise ConflictError("restore receipt binding mismatch")
        if expected_source_snapshot_hash is not None:
            if evidence["source_snapshot_hash"] != expected_source_snapshot_hash:
                raise ConflictError("restore source snapshot binding mismatch")
            if (
                source_snapshot is not None
                and sha256_hex(canonical_bytes(source_snapshot)) != expected_source_snapshot_hash
            ):
                raise ConflictError("restore source snapshot hash mismatch")
        if expected_output is not None:
            expected_output_text = expected_output.decode("utf-8")
            if (
                evidence["expected_output_sha256"] != sha256_hex(expected_output)
                or evidence["expected_output_bytes"] != expected_output_text
            ):
                raise ConflictError("restore output binding mismatch")
        if source_snapshot_validator is not None:
            source_snapshot_validator()
        if evidence["operation_status"] != "bound-and-config-published":
            raise ArsError("restore binding output publication is incomplete")
        if evidence["durability_status"] != "durable":
            raise ArsError("restore binding durability is incomplete")
        return manifest
    if evidence is not None:
        raise ConflictError("restore binding evidence conflicts with an unbound manifest")

    rebound = dict(manifest)
    rebound["control_root"] = str(target)
    rebound["manifest_hash"] = _manifest_hash(rebound)
    if set(rebound).difference({"control_root", "manifest_hash"}) != set(manifest).difference(
        {"control_root", "manifest_hash"}
    ):
        raise IntegrityError("restore rebind changed manifest fields")
    data = canonical_bytes(rebound)
    expected_output_text = expected_output.decode("utf-8") if expected_output is not None else ""
    source_snapshot_value = source_snapshot or {}
    source_snapshot_hash = expected_source_snapshot_hash or (
        sha256_hex(canonical_bytes(source_snapshot_value)) if source_snapshot else ""
    )
    if expected_source_snapshot_hash is not None:
        if source_snapshot is None or sha256_hex(canonical_bytes(source_snapshot)) != expected_source_snapshot_hash:
            raise ConflictError("restore source snapshot hash mismatch")
    evidence = {
        "source_root": str(source),
        "target_root": str(target),
        "project_id": str(manifest["project_id"]),
        "store_identity": str(manifest["store_identity"]),
        "manifest_hash": rebound["manifest_hash"],
        "receipt_hash": expected_restore_receipt_hash or "",
        "source_snapshot": source_snapshot_value,
        "source_snapshot_hash": source_snapshot_hash,
        "operation_status": "bound-and-config-published",
        "durability_status": "durable",
        "expected_output_bytes": expected_output_text,
        "expected_output_sha256": sha256_hex(expected_output) if expected_output is not None else "",
        "target_manifest_bytes_sha256": sha256_hex(data),
    }
    if expected_output is not None and output_commit is None:
        raise ArsError("restore output publisher is required before binding")
    evidence_path = _restore_binding_evidence_path(target)
    evidence_temporary = evidence_path.with_name(f".{evidence_path.name}.{secrets.token_hex(16)}.tmp")
    temporary = manifest_path.with_name(f".{manifest_path.name}.{secrets.token_hex(16)}.tmp")
    descriptor = -1
    manifest_published = False
    evidence_published = False
    output_attempted = False

    def write_temporary(path: Path, value: bytes) -> None:
        nonlocal descriptor
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

    def restore_original_manifest() -> None:
        rollback = manifest_path.with_name(f".{manifest_path.name}.{secrets.token_hex(16)}.rollback")
        rollback_descriptor = -1
        try:
            rollback_descriptor = os.open(rollback, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(rollback_descriptor, "wb") as handle:
                rollback_descriptor = -1
                handle.write(original_manifest_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(rollback, manifest_path)
            if not _fsync_directory(manifest_path.parent):
                raise ArsError("restore binding rollback durability is unavailable")
        finally:
            if rollback_descriptor != -1:
                os.close(rollback_descriptor)
            rollback.unlink(missing_ok=True)

    try:
        write_temporary(temporary, data)
        write_temporary(evidence_temporary, canonical_bytes(evidence))
        _before_restore_manifest_replace()
        if source_snapshot_validator is not None:
            source_snapshot_validator()
        if (
            expected_target_manifest_bytes_sha256 is not None
            and original_manifest_bytes_sha256 != expected_target_manifest_bytes_sha256
        ):
            raise ConflictError("target manifest changed before restore binding")
        if output_commit is not None:
            output_attempted = True
            published_output = output_commit()
            if published_output is False:
                raise ArsError("restore binding requires durable output publication")
        os.replace(temporary, manifest_path)
        manifest_published = True
        if not _fsync_directory(manifest_path.parent):
            raise ArsError("restore binding requires durable manifest publication")
        os.replace(evidence_temporary, evidence_path)
        evidence_published = True
        if not _fsync_directory(evidence_path.parent):
            raise ArsError("restore binding requires durable evidence publication")
        if post_commit is not None:
            post_commit()
    except BaseException:
        if evidence_published:
            evidence_path.unlink(missing_ok=True)
        if manifest_published:
            restore_original_manifest()
        if output_attempted and output_rollback is not None:
            output_rollback()
        raise
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
        evidence_temporary.unlink(missing_ok=True)
    return rebound


def complete_restore_binding_output(
    control_root: Path,
    output_path: Path,
    expected_output: bytes,
    *,
    directory_durable: bool = True,
) -> dict[str, Any]:
    """Complete the durable config side of a committed restore binding."""
    target = control_root.resolve(strict=True)
    evidence, evidence_path = _read_restore_binding_evidence(target, include_pending=True)
    if evidence is None:
        raise IntegrityError("restore binding evidence is missing")
    if not directory_durable or not _fsync_directory(target / "manifests"):
        raise ArsError("restore binding requires durable evidence directory")
    expected_text = expected_output.decode("utf-8")
    expected_hash = sha256_hex(expected_output)
    if evidence["expected_output_sha256"] != expected_hash or evidence["expected_output_bytes"] != expected_text:
        raise ConflictError("restore output binding mismatch")
    output = output_path.resolve(strict=False)
    if not output.is_file():
        raise ArsError(f"restore binding status=bound-but-config-unpublished; expected output sha256={expected_hash}")
    try:
        actual = output.read_bytes()
    except OSError as exc:
        raise ArsError(
            f"restore binding status=bound-but-config-unpublished; expected output sha256={expected_hash}"
        ) from exc
    if actual != expected_output:
        raise ConflictError(
            f"restore binding status=bound-but-config-unpublished; expected output sha256={expected_hash}"
        )
    if not _fsync_directory(output.parent):
        raise ArsError("restore binding requires durable output directory")
    evidence["operation_status"] = "bound-and-config-published"
    evidence["durability_status"] = "durable"
    try:
        evidence_durable = _write_restore_binding_pending(
            target,
            evidence,
            replace=evidence_path == _restore_binding_pending_path(target),
        )
        if not evidence_durable:
            raise ArsError("restore binding requires durable evidence publication")
        publication_durable = _publish_restore_binding_pending(target)
        if not publication_durable:
            raise ArsError("restore binding requires durable evidence publication")
    except BaseException:
        _restore_binding_pending_path(target).unlink(missing_ok=True)
        raise
    return evidence


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
