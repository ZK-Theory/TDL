from __future__ import annotations

import errno
import json
import os
import secrets
from pathlib import Path
from typing import Any, Callable

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.layout import (
    require_existing_control_root,
    require_external_control_root,
)

_IDENTITY_NAME = "store-identity.json"
_RESTORE_BINDING_EVIDENCE_NAME = "restore-binding-evidence.json"
_RESTORE_BINDING_TRANSACTION_NAME = ".restore-binding-transaction.json"
_RESTORE_BINDING_OUTPUT_DIRECTORY = "restore-bindings"
_LEGACY_RESTORE_AUTHORITY_NAMES = frozenset(
    {
        ".restore-binding-evidence.pending",
        ".restore-binding-journal.json",
        ".restore-binding-recovery.json",
    }
)
_RESTORE_STATES = ("prepared", "published", "final_validated", "committed", "cleared")
_RESTORE_STEPS = (
    "prepared-record-durable",
    "output-object-durable",
    "manifest-durable",
    "evidence-durable",
    "published-record-durable",
    "final-validation-durable",
    "commit-durable",
    "clear-durable",
)
_SCHEMA_SUFFIX = Path(".research-system") / "schemas"
SCHEMA_BINDING_VERSION = "1.0.0"


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


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
    """Load a source-bound manifest for the explicit restore finalization path."""
    control = control_root.resolve(strict=True)
    manifest = _read_manifest(_manifest_path(control), require_canonical=True)
    _validate_manifest_identity(manifest)
    return manifest


def manifest_schema_root(manifest: dict[str, Any]) -> Path | None:
    """Return a structurally verified canonical schema binding, if persisted."""
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
        descriptor = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ConflictError(f"control store already initialized: {control}") from exc
    with os.fdopen(descriptor, "wb") as handle:
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


def canonical_restore_binding_output(
    target_root: Path,
    project_id: str,
    store_identity: str,
    code_roots: list[Path] | tuple[Path, ...],
    schema_root: Path,
) -> bytes:
    """Derive the only canonical binding bytes admitted by a restore transaction."""
    target = target_root.resolve(strict=False)
    codes = sorted(str(root.resolve(strict=True)) for root in code_roots)
    schema = schema_root.resolve(strict=True)
    return canonical_bytes(
        {
            "code_roots": codes,
            "control_root": str(target),
            "project_id": validate_id(project_id, "project"),
            "schema_root": str(schema),
            "store_identity": store_identity,
        }
    )


def _restore_binding_evidence_path(control_root: Path) -> Path:
    return control_root / "manifests" / _RESTORE_BINDING_EVIDENCE_NAME


def restore_binding_transaction_path(control_root: Path) -> Path:
    return control_root / "manifests" / _RESTORE_BINDING_TRANSACTION_NAME


def restore_binding_output_object_path(control_root: Path, digest: str) -> Path:
    if not _is_sha256(digest):
        raise IntegrityError("restore binding output digest is invalid")
    return control_root / "manifests" / _RESTORE_BINDING_OUTPUT_DIRECTORY / f"sha256-{digest}.json"


def _relative_path(target: Path, path: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError as exc:
        raise IntegrityError("restore binding path escapes the target store") from exc


def _record_path(target: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise IntegrityError("restore binding relative path is invalid")
    path = target.joinpath(*relative.split("/"))
    try:
        path.resolve(strict=False).relative_to(target.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise IntegrityError("restore binding path escapes the target store") from exc
    return path


def _file_bytes(path: Path) -> bytes | None:
    try:
        if not path.exists():
            return None
        if not path.is_file():
            raise ConflictError(f"restore binding path is not a file: {path}")
        return path.read_bytes()
    except ConflictError:
        raise
    except OSError as exc:
        raise ConflictError(f"restore binding path is unavailable: {path}") from exc


def _hex_bytes(value: bytes | None) -> str | None:
    return value.hex() if value is not None else None


def _from_hex(value: Any, field: str) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) % 2:
        raise IntegrityError(f"restore binding transaction field is invalid: {field}")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise IntegrityError(f"restore binding transaction field is invalid: {field}") from exc


def _physical_root_identity(path: Path) -> dict[str, str]:
    try:
        metadata = path.stat()
    except OSError as exc:
        raise ArsError(f"restore binding root identity is unavailable: {path}") from exc
    return {"device": str(metadata.st_dev), "inode": str(metadata.st_ino)}


def _require_root_identity(path: Path, expected: dict[str, Any]) -> None:
    if _physical_root_identity(path) != expected:
        raise ConflictError(f"restore binding physical root identity changed: {path}")


def _assert_no_second_restore_authority(target: Path) -> None:
    manifests = target / "manifests"
    for name in _LEGACY_RESTORE_AUTHORITY_NAMES:
        if (manifests / name).exists():
            raise IntegrityError(f"second restore recovery authority exists: {name}")
    canonical = restore_binding_transaction_path(target)
    for candidate in manifests.glob(".restore-binding-*.json"):
        if candidate != canonical:
            raise IntegrityError(f"second restore recovery authority exists: {candidate.name}")


_EVIDENCE_FIELDS = frozenset(
    {
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
        "transaction_id",
        "output_object_path",
        "output_object_sha256",
        "actor_id",
        "authority_grant_id",
        "code_roots",
        "schema_root",
    }
)


def _validate_restore_binding_evidence(target: Path, value: dict[str, Any], raw: bytes) -> None:
    if raw != canonical_bytes(value) or set(value) != _EVIDENCE_FIELDS:
        raise IntegrityError("restore binding evidence fields are invalid")
    snapshot = value["source_snapshot"]
    output_text = value["expected_output_bytes"]
    output_digest = value["output_object_sha256"]
    code_roots = value["code_roots"]
    if (
        not isinstance(snapshot, dict)
        or value["source_snapshot_hash"] != sha256_hex(canonical_bytes(snapshot))
        or not isinstance(output_text, str)
        or value["expected_output_sha256"] != sha256_hex(output_text.encode("utf-8"))
        or value["expected_output_sha256"] != output_digest
        or value["operation_status"] != "bound-and-config-published"
        or value["durability_status"] != "durable"
        or not isinstance(code_roots, list)
        or not code_roots
        or any(not isinstance(root, str) or not Path(root).is_absolute() for root in code_roots)
        or not isinstance(value["schema_root"], str)
        or not Path(value["schema_root"]).is_absolute()
    ):
        raise IntegrityError("restore binding evidence values are invalid")
    for field in (
        "manifest_hash",
        "receipt_hash",
        "source_snapshot_hash",
        "expected_output_sha256",
        "target_manifest_bytes_sha256",
        "output_object_sha256",
    ):
        item = value[field]
        if not _is_sha256(item):
            raise IntegrityError(f"restore binding evidence digest is invalid: {field}")
    source = Path(str(value["source_root"]))
    recorded_target = Path(str(value["target_root"]))
    if not source.is_absolute() or not recorded_target.is_absolute():
        raise IntegrityError("restore binding evidence root is invalid")
    if recorded_target.resolve(strict=False) != target or source.resolve(strict=False) == target:
        raise IntegrityError("restore binding evidence root join is invalid")
    output = _record_path(target, str(value["output_object_path"]))
    if output != restore_binding_output_object_path(target, output_digest):
        raise IntegrityError("restore binding evidence output path is invalid")


def _read_restore_binding_evidence(control_root: Path) -> tuple[dict[str, Any] | None, bytes | None]:
    target = control_root.resolve(strict=True)
    raw = _file_bytes(_restore_binding_evidence_path(target))
    if raw is None:
        return None, None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("restore binding evidence is invalid") from exc
    if not isinstance(value, dict):
        raise IntegrityError("restore binding evidence is invalid")
    _validate_restore_binding_evidence(target, value, raw)
    return value, raw


def load_restore_binding_evidence(control_root: Path) -> dict[str, Any] | None:
    value, _ = _read_restore_binding_evidence(control_root)
    return value


def load_canonical_restore_binding_evidence(control_root: Path) -> dict[str, Any] | None:
    value, _ = _read_restore_binding_evidence(control_root)
    return value


_TRANSACTION_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "transaction_id",
        "state",
        "generation",
        "prior_record_sha256",
        "last_completed_durability_step",
        "source_root",
        "target_root",
        "source_root_identity",
        "target_root_identity",
        "project_id",
        "store_identity",
        "receipt_hash",
        "actor_id",
        "authority_grant_id",
        "source_snapshot",
        "source_snapshot_hash",
        "code_roots",
        "schema_root",
        "target_pre_state_sha256",
        "original_manifest_bytes",
        "original_manifest_sha256",
        "intended_manifest_bytes",
        "intended_manifest_sha256",
        "original_evidence_bytes",
        "original_evidence_sha256",
        "intended_evidence_bytes",
        "intended_evidence_sha256",
        "output_object_path",
        "output_object_sha256",
        "output_object_bytes",
        "temporaries",
    }
)


def _validate_restore_binding_transaction(target: Path, value: dict[str, Any], raw: bytes) -> None:
    if raw != canonical_bytes(value) or set(value) != _TRANSACTION_FIELDS:
        raise IntegrityError("restore binding transaction fields are invalid")
    if (
        value["schema_id"] != "ars://internal/restore-binding-transaction"
        or value["schema_version"] != "1.0.0"
        or value["state"] not in _RESTORE_STATES
        or value["last_completed_durability_step"] not in _RESTORE_STEPS
        or isinstance(value["generation"], bool)
        or not isinstance(value["generation"], int)
        or value["generation"] < 0
        or not _is_sha256(value["transaction_id"])
    ):
        raise IntegrityError("restore binding transaction identity is invalid")
    state_steps = {
        "prepared": {
            "prepared-record-durable",
            "output-object-durable",
            "manifest-durable",
            "evidence-durable",
        },
        "published": {"published-record-durable"},
        "final_validated": {"final-validation-durable"},
        "committed": {"commit-durable"},
        "cleared": {"clear-durable"},
    }
    if value["last_completed_durability_step"] not in state_steps[value["state"]] or value[
        "generation"
    ] != _RESTORE_STEPS.index(value["last_completed_durability_step"]):
        raise IntegrityError("restore binding transaction state/generation is invalid")
    prior = value["prior_record_sha256"]
    if (value["generation"] == 0 and prior != "") or (value["generation"] > 0 and not _is_sha256(prior)):
        raise IntegrityError("restore binding transaction generation chain is invalid")
    source = Path(str(value["source_root"]))
    recorded_target = Path(str(value["target_root"]))
    if (
        not source.is_absolute()
        or not recorded_target.is_absolute()
        or recorded_target.resolve(strict=False) != target
        or source.resolve(strict=False) == target
    ):
        raise IntegrityError("restore binding transaction root is invalid")
    for identity_field in ("source_root_identity", "target_root_identity"):
        identity = value[identity_field]
        if (
            not isinstance(identity, dict)
            or set(identity) != {"device", "inode"}
            or any(not isinstance(item, str) or not item.isdecimal() for item in identity.values())
        ):
            raise IntegrityError(f"restore binding transaction root identity is invalid: {identity_field}")
    code_roots = value["code_roots"]
    if (
        not isinstance(code_roots, list)
        or not code_roots
        or any(not isinstance(root, str) or not Path(root).is_absolute() for root in code_roots)
        or not isinstance(value["schema_root"], str)
        or not Path(value["schema_root"]).is_absolute()
        or not isinstance(value["source_snapshot"], dict)
        or value["source_snapshot_hash"] != sha256_hex(canonical_bytes(value["source_snapshot"]))
    ):
        raise IntegrityError("restore binding transaction approved input is invalid")
    byte_fields = (
        ("original_manifest_bytes", "original_manifest_sha256", False),
        ("intended_manifest_bytes", "intended_manifest_sha256", False),
        ("original_evidence_bytes", "original_evidence_sha256", True),
        ("intended_evidence_bytes", "intended_evidence_sha256", False),
        ("output_object_bytes", "output_object_sha256", False),
    )
    for bytes_field, digest_field, nullable in byte_fields:
        item = _from_hex(value[bytes_field], bytes_field)
        digest = value[digest_field]
        if item is None:
            if not nullable or digest != "":
                raise IntegrityError(f"restore binding transaction bytes are invalid: {bytes_field}")
        elif not isinstance(digest, str) or digest != sha256_hex(item):
            raise IntegrityError(f"restore binding transaction digest is invalid: {digest_field}")
    if value["target_pre_state_sha256"] != value["original_manifest_sha256"]:
        raise IntegrityError("restore binding transaction pre-state is invalid")
    output = _record_path(target, str(value["output_object_path"]))
    if output != restore_binding_output_object_path(target, str(value["output_object_sha256"])):
        raise IntegrityError("restore binding transaction output path is invalid")
    temporaries = value["temporaries"]
    if not isinstance(temporaries, dict) or set(temporaries) != {"output", "manifest", "evidence"}:
        raise IntegrityError("restore binding transaction temporary identities are invalid")
    expected_digests = {
        "output": value["output_object_sha256"],
        "manifest": value["intended_manifest_sha256"],
        "evidence": value["intended_evidence_sha256"],
    }
    for name, temporary in temporaries.items():
        if (
            not isinstance(temporary, dict)
            or set(temporary) != {"relative_path", "sha256"}
            or temporary["sha256"] != expected_digests[name]
        ):
            raise IntegrityError(f"restore binding transaction temporary is invalid: {name}")
        _record_path(target, str(temporary["relative_path"]))


def _read_restore_binding_transaction(control_root: Path) -> tuple[dict[str, Any] | None, bytes | None]:
    target = control_root.resolve(strict=True)
    _assert_no_second_restore_authority(target)
    raw = _file_bytes(restore_binding_transaction_path(target))
    if raw is None:
        return None, None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("restore binding transaction is invalid") from exc
    if not isinstance(value, dict):
        raise IntegrityError("restore binding transaction is invalid")
    _validate_restore_binding_transaction(target, value, raw)
    return value, raw


def load_restore_binding_transaction(control_root: Path) -> dict[str, Any] | None:
    value, _ = _read_restore_binding_transaction(control_root)
    return value


def _write_exclusive(path: Path, data: bytes) -> None:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _after_restore_transaction_state_written(path: Path, state: str, generation: int) -> None:
    """Test seam after one state generation and its directory entry are durable."""


def _before_restore_manifest_replace() -> None:
    """Test seam immediately before manifest ownership comparison and replacement."""


def _before_restore_owned_temporary_cleanup(path: Path) -> None:
    """Test seam immediately before cleanup rechecks a transaction-owned temporary."""


def _transaction_transition_path(target: Path, transaction_id: str, generation: int) -> Path:
    return target / "manifests" / f".restore-binding-transaction.{transaction_id}.{generation}.tmp"


def _cleanup_owned_temporary(path: Path, expected: bytes) -> None:
    if not path.exists():
        return
    _before_restore_owned_temporary_cleanup(path)
    actual = _file_bytes(path)
    if actual != expected:
        raise ConflictError(f"restore binding temporary ownership changed: {path}")
    path.unlink()
    if not _fsync_directory(path.parent):
        raise ArsError("restore binding requires durable temporary cleanup")


def _cleanup_current_transaction_temporary(target: Path, record: dict[str, Any], record_raw: bytes) -> None:
    temporary = _transaction_transition_path(
        target,
        str(record["transaction_id"]),
        int(record["generation"]),
    )
    _cleanup_owned_temporary(temporary, record_raw)


def _write_initial_transaction(target: Path, value: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    path = restore_binding_transaction_path(target)
    data = canonical_bytes(value)
    temporary = _transaction_transition_path(target, str(value["transaction_id"]), 0)
    existing = _file_bytes(temporary)
    if existing is None:
        _write_exclusive(temporary, data)
    elif existing != data:
        raise ConflictError("restore binding prepared-record temporary conflicts")
    try:
        os.link(temporary, path)
    except FileExistsError as exc:
        raise ConflictError("restore binding transaction already exists") from exc
    if not _fsync_directory(path.parent):
        raise ArsError("restore binding requires durable prepared transaction")
    _cleanup_owned_temporary(temporary, data)
    _after_restore_transaction_state_written(path, "prepared", 0)
    return value, data


def _transition_transaction(
    target: Path,
    current: dict[str, Any],
    current_raw: bytes,
    *,
    state: str,
    durability_step: str,
) -> tuple[dict[str, Any], bytes]:
    if state not in _RESTORE_STATES or durability_step not in _RESTORE_STEPS:
        raise IntegrityError("restore binding transaction transition is invalid")
    if _RESTORE_STATES.index(state) < _RESTORE_STATES.index(str(current["state"])):
        raise IntegrityError("restore binding transaction state cannot move backwards")
    if _RESTORE_STEPS.index(durability_step) <= _RESTORE_STEPS.index(str(current["last_completed_durability_step"])):
        raise IntegrityError("restore binding transaction durability step cannot move backwards")
    next_value = dict(current)
    next_value["state"] = state
    next_value["generation"] = int(current["generation"]) + 1
    next_value["prior_record_sha256"] = sha256_hex(current_raw)
    next_value["last_completed_durability_step"] = durability_step
    next_raw = canonical_bytes(next_value)
    path = restore_binding_transaction_path(target)
    temporary = _transaction_transition_path(
        target,
        str(current["transaction_id"]),
        int(next_value["generation"]),
    )
    existing = _file_bytes(temporary)
    if existing is None:
        _write_exclusive(temporary, next_raw)
    elif existing != next_raw:
        raise ConflictError("restore binding transaction transition temporary conflicts")
    if _file_bytes(path) != current_raw:
        raise ConflictError("restore binding transaction changed before state transition")
    os.replace(temporary, path)
    if not _fsync_directory(path.parent):
        raise ArsError("restore binding requires durable transaction transition")
    _after_restore_transaction_state_written(path, state, int(next_value["generation"]))
    return next_value, next_raw


def _owned_temporary(target: Path, record: dict[str, Any], name: str) -> tuple[Path, bytes]:
    item = record["temporaries"][name]
    path = _record_path(target, str(item["relative_path"]))
    if name == "output":
        data = _from_hex(record["output_object_bytes"], "output_object_bytes")
    elif name == "manifest":
        data = _from_hex(record["intended_manifest_bytes"], "intended_manifest_bytes")
    else:
        data = _from_hex(record["intended_evidence_bytes"], "intended_evidence_bytes")
    if data is None or sha256_hex(data) != item["sha256"]:
        raise IntegrityError(f"restore binding transaction temporary digest is invalid: {name}")
    return path, data


def _prepare_owned_temporary(target: Path, record: dict[str, Any], name: str) -> tuple[Path, bytes]:
    path, data = _owned_temporary(target, record, name)
    existing = _file_bytes(path)
    if existing is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_exclusive(path, data)
        if not _fsync_directory(path.parent):
            raise ArsError("restore binding requires durable temporary preparation")
    elif existing != data:
        raise ConflictError(f"restore binding temporary ownership conflict: {path}")
    return path, data


def _publish_output_object(target: Path, record: dict[str, Any]) -> None:
    output = _record_path(target, str(record["output_object_path"]))
    expected = _from_hex(record["output_object_bytes"], "output_object_bytes")
    if expected is None:
        raise IntegrityError("restore binding output bytes are missing")
    existing = _file_bytes(output)
    if existing is not None:
        if existing != expected or sha256_hex(existing) != record["output_object_sha256"]:
            raise ConflictError(f"restore binding content-addressed output conflicts: {output}")
        temporary, temporary_bytes = _owned_temporary(target, record, "output")
        _cleanup_owned_temporary(temporary, temporary_bytes)
        return
    temporary, temporary_bytes = _prepare_owned_temporary(target, record, "output")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(temporary, output)
    except FileExistsError:
        actual = _file_bytes(output)
        if actual != expected:
            raise ConflictError(f"restore binding content-addressed output conflicts: {output}")
    if _file_bytes(output) != expected:
        raise ConflictError(f"restore binding content-addressed output conflicts: {output}")
    if not _fsync_directory(output.parent):
        raise ArsError("restore binding requires durable output publication")
    _cleanup_owned_temporary(temporary, temporary_bytes)


def _publish_mutable_object(
    target: Path,
    record: dict[str, Any],
    *,
    name: str,
    path: Path,
    original: bytes | None,
    intended: bytes,
    mutation_validator: Callable[[], None] | None = None,
) -> None:
    live = _file_bytes(path)
    if live == intended:
        temporary, temporary_bytes = _owned_temporary(target, record, name)
        _cleanup_owned_temporary(temporary, temporary_bytes)
        return
    if live != original:
        raise ConflictError(f"restore binding canonical path changed: {path}")
    temporary, temporary_bytes = _prepare_owned_temporary(target, record, name)
    if name == "manifest":
        _before_restore_manifest_replace()
    if mutation_validator is not None:
        mutation_validator()
    if _file_bytes(path) != original:
        raise ConflictError(f"restore binding canonical path changed at mutation seam: {path}")
    if original is None:
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise ConflictError(f"restore binding canonical path changed at mutation seam: {path}") from exc
    else:
        os.replace(temporary, path)
    if _file_bytes(path) != intended:
        raise ConflictError(f"restore binding canonical publication conflicts: {path}")
    if not _fsync_directory(path.parent):
        raise ArsError("restore binding requires durable canonical publication")
    _cleanup_owned_temporary(temporary, temporary_bytes)


def _build_restore_evidence(
    *,
    transaction_id: str,
    source: Path,
    target: Path,
    project_id: str,
    store_identity: str,
    manifest: dict[str, Any],
    manifest_bytes: bytes,
    receipt_hash: str,
    source_snapshot: dict[str, Any],
    source_snapshot_hash: str,
    output_bytes: bytes,
    output_relative: str,
    actor_id: str,
    authority_grant_id: str,
    code_roots: list[str],
    schema_root: str,
) -> dict[str, Any]:
    output_digest = sha256_hex(output_bytes)
    return {
        "source_root": str(source),
        "target_root": str(target),
        "project_id": project_id,
        "store_identity": store_identity,
        "manifest_hash": manifest["manifest_hash"],
        "receipt_hash": receipt_hash,
        "source_snapshot": source_snapshot,
        "source_snapshot_hash": source_snapshot_hash,
        "operation_status": "bound-and-config-published",
        "durability_status": "durable",
        "expected_output_bytes": output_bytes.decode("utf-8"),
        "expected_output_sha256": output_digest,
        "target_manifest_bytes_sha256": sha256_hex(manifest_bytes),
        "transaction_id": transaction_id,
        "output_object_path": output_relative,
        "output_object_sha256": output_digest,
        "actor_id": actor_id,
        "authority_grant_id": authority_grant_id,
        "code_roots": code_roots,
        "schema_root": schema_root,
    }


def _build_restore_transaction(
    *,
    transaction_id: str,
    source: Path,
    target: Path,
    project_id: str,
    store_identity: str,
    receipt_hash: str,
    actor_id: str,
    authority_grant_id: str,
    source_snapshot: dict[str, Any],
    source_snapshot_hash: str,
    code_roots: list[str],
    schema_root: str,
    original_manifest: bytes,
    intended_manifest: bytes,
    original_evidence: bytes | None,
    intended_evidence: bytes,
    output_bytes: bytes,
) -> dict[str, Any]:
    output_digest = sha256_hex(output_bytes)
    output_path = restore_binding_output_object_path(target, output_digest)
    output_relative = _relative_path(target, output_path)
    return {
        "schema_id": "ars://internal/restore-binding-transaction",
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "state": "prepared",
        "generation": 0,
        "prior_record_sha256": "",
        "last_completed_durability_step": "prepared-record-durable",
        "source_root": str(source),
        "target_root": str(target),
        "source_root_identity": _physical_root_identity(source),
        "target_root_identity": _physical_root_identity(target),
        "project_id": project_id,
        "store_identity": store_identity,
        "receipt_hash": receipt_hash,
        "actor_id": actor_id,
        "authority_grant_id": authority_grant_id,
        "source_snapshot": source_snapshot,
        "source_snapshot_hash": source_snapshot_hash,
        "code_roots": code_roots,
        "schema_root": schema_root,
        "target_pre_state_sha256": sha256_hex(original_manifest),
        "original_manifest_bytes": _hex_bytes(original_manifest),
        "original_manifest_sha256": sha256_hex(original_manifest),
        "intended_manifest_bytes": _hex_bytes(intended_manifest),
        "intended_manifest_sha256": sha256_hex(intended_manifest),
        "original_evidence_bytes": _hex_bytes(original_evidence),
        "original_evidence_sha256": sha256_hex(original_evidence) if original_evidence is not None else "",
        "intended_evidence_bytes": _hex_bytes(intended_evidence),
        "intended_evidence_sha256": sha256_hex(intended_evidence),
        "output_object_path": output_relative,
        "output_object_sha256": output_digest,
        "output_object_bytes": _hex_bytes(output_bytes),
        "temporaries": {
            "output": {
                "relative_path": f"manifests/{_RESTORE_BINDING_OUTPUT_DIRECTORY}/.{output_path.name}.{transaction_id}.tmp",
                "sha256": output_digest,
            },
            "manifest": {
                "relative_path": f"manifests/.{_IDENTITY_NAME}.{transaction_id}.tmp",
                "sha256": sha256_hex(intended_manifest),
            },
            "evidence": {
                "relative_path": f"manifests/.{_RESTORE_BINDING_EVIDENCE_NAME}.{transaction_id}.tmp",
                "sha256": sha256_hex(intended_evidence),
            },
        },
    }


def _validate_record_inputs(
    record: dict[str, Any],
    *,
    source: Path,
    target: Path,
    project_id: str,
    store_identity: str,
    receipt_hash: str,
    actor_id: str,
    authority_grant_id: str,
    source_snapshot_hash: str,
    code_roots: list[str],
    schema_root: str,
    output_bytes: bytes,
) -> None:
    expected = {
        "source_root": str(source),
        "target_root": str(target),
        "project_id": project_id,
        "store_identity": store_identity,
        "receipt_hash": receipt_hash,
        "actor_id": actor_id,
        "authority_grant_id": authority_grant_id,
        "source_snapshot_hash": source_snapshot_hash,
        "code_roots": code_roots,
        "schema_root": schema_root,
        "output_object_sha256": sha256_hex(output_bytes),
        "output_object_bytes": _hex_bytes(output_bytes),
    }
    for field, value in expected.items():
        if record[field] != value:
            raise ConflictError(f"restore binding transaction input changed: {field}")
    _require_root_identity(source, record["source_root_identity"])
    _require_root_identity(target, record["target_root_identity"])


def _validate_restore_join(target: Path, record: dict[str, Any]) -> dict[str, Any]:
    manifest_path = _manifest_path(target)
    evidence_path = _restore_binding_evidence_path(target)
    output_path = _record_path(target, str(record["output_object_path"]))
    intended_manifest = _from_hex(record["intended_manifest_bytes"], "intended_manifest_bytes")
    intended_evidence = _from_hex(record["intended_evidence_bytes"], "intended_evidence_bytes")
    output_bytes = _from_hex(record["output_object_bytes"], "output_object_bytes")
    if intended_manifest is None or intended_evidence is None or output_bytes is None:
        raise IntegrityError("restore binding transaction intended tuple is incomplete")
    if _file_bytes(manifest_path) != intended_manifest:
        raise IntegrityError("restore binding manifest does not match the transaction")
    if _file_bytes(evidence_path) != intended_evidence:
        raise IntegrityError("restore binding evidence does not match the transaction")
    actual_output = _file_bytes(output_path)
    if actual_output != output_bytes or sha256_hex(actual_output or b"") != record["output_object_sha256"]:
        raise IntegrityError("restore binding output does not match the transaction")
    manifest = _read_manifest(manifest_path, require_canonical=True)
    evidence, evidence_raw = _read_restore_binding_evidence(target)
    if evidence is None or evidence_raw != intended_evidence:
        raise IntegrityError("restore binding evidence join is missing")
    if (
        evidence["transaction_id"] != record["transaction_id"]
        or evidence["output_object_path"] != record["output_object_path"]
        or evidence["output_object_sha256"] != record["output_object_sha256"]
        or evidence["target_manifest_bytes_sha256"] != record["intended_manifest_sha256"]
        or evidence["manifest_hash"] != manifest["manifest_hash"]
        or evidence["project_id"] != record["project_id"]
        or evidence["store_identity"] != record["store_identity"]
        or evidence["source_snapshot_hash"] != record["source_snapshot_hash"]
        or evidence["receipt_hash"] != record["receipt_hash"]
        or evidence["actor_id"] != record["actor_id"]
        or evidence["authority_grant_id"] != record["authority_grant_id"]
    ):
        raise IntegrityError("restore binding transaction/evidence/manifest/output join is invalid")
    return manifest


def _require_cleared_without_temporaries(target: Path, record: dict[str, Any]) -> None:
    transition_temporaries = any((target / "manifests").glob(".restore-binding-transaction.*.tmp"))
    if transition_temporaries or any(
        _record_path(target, str(item["relative_path"])).exists() for item in record["temporaries"].values()
    ):
        raise IntegrityError("cleared restore binding retains a transaction temporary")


def rebind_restored_store(
    target_root: Path,
    source_root: Path,
    *,
    expected_project_id: str | None = None,
    expected_store_identity: str | None = None,
    expected_code_roots: list[Path] | None = None,
    expected_schema_root: Path | None = None,
    expected_restore_receipt_hash: str | None = None,
    actor_id: str | None = None,
    authority_grant_id: str | None = None,
    source_snapshot: dict[str, Any] | None = None,
    expected_source_snapshot_hash: str | None = None,
    expected_target_manifest_bytes_sha256: str | None = None,
    expected_output: bytes | None = None,
    source_snapshot_validator: Callable[[], None] | None = None,
    finalization_validator: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Complete or resume the single durable restore-binding transaction."""
    if (
        expected_project_id is None
        or expected_store_identity is None
        or expected_code_roots is None
        or expected_schema_root is None
        or expected_restore_receipt_hash is None
        or actor_id is None
        or authority_grant_id is None
        or source_snapshot is None
        or expected_source_snapshot_hash is None
    ):
        raise ArsError("complete approved restore transaction inputs are required")
    code_paths = [root.resolve(strict=True) for root in expected_code_roots]
    target = require_existing_control_root(code_paths, target_root)
    source = require_existing_control_root(code_paths, source_root)
    if source == target:
        raise ConflictError("restored store source must differ from target")
    schema = expected_schema_root.resolve(strict=True)
    code_values = sorted(str(root) for root in code_paths)
    output_bytes = expected_output or canonical_restore_binding_output(
        target,
        expected_project_id,
        expected_store_identity,
        code_paths,
        schema,
    )
    canonical_output = canonical_restore_binding_output(
        target,
        expected_project_id,
        expected_store_identity,
        code_paths,
        schema,
    )
    if output_bytes != canonical_output:
        raise ConflictError("restore binding output differs from approved canonical bytes")
    if sha256_hex(canonical_bytes(source_snapshot)) != expected_source_snapshot_hash:
        raise ConflictError("restore source snapshot hash mismatch")

    def validate_physical_roots(record_value: dict[str, Any]) -> None:
        require_existing_control_root(code_paths, source)
        require_existing_control_root(code_paths, target)
        _require_root_identity(source, record_value["source_root_identity"])
        _require_root_identity(target, record_value["target_root_identity"])

    _assert_no_second_restore_authority(target)
    record, record_raw = _read_restore_binding_transaction(target)
    manifest_path = _manifest_path(target)
    evidence_path = _restore_binding_evidence_path(target)

    if record is None:
        original_manifest = _file_bytes(manifest_path)
        if original_manifest is None:
            raise IntegrityError("restore source manifest is missing")
        manifest = load_store_manifest_unbound(target)
        current_root = Path(str(manifest.get("control_root", ""))).resolve(strict=False)
        if current_root == target:
            raise IntegrityError("journal-less restored manifest cannot be finalized")
        if current_root != source:
            raise ConflictError("restored store source binding mismatch")
        if _file_bytes(evidence_path) is not None:
            raise IntegrityError("restore evidence exists without a transaction record")
        if expected_target_manifest_bytes_sha256 is not None and sha256_hex(original_manifest) != (
            expected_target_manifest_bytes_sha256
        ):
            raise ConflictError("target manifest changed before restore binding")
        if manifest.get("project_id") != expected_project_id:
            raise ConflictError("project identity mismatch")
        if manifest.get("store_identity") != expected_store_identity:
            raise ConflictError("store identity mismatch")
        if manifest.get("code_roots") != code_values:
            raise ConflictError("code root binding mismatch")
        persisted_schema = manifest_schema_root(manifest)
        if persisted_schema is None or persisted_schema.resolve(strict=False) != schema:
            raise ConflictError("schema root binding mismatch")
        rebound = dict(manifest)
        rebound["control_root"] = str(target)
        rebound["manifest_hash"] = _manifest_hash(rebound)
        intended_manifest = canonical_bytes(rebound)
        transaction_id = secrets.token_hex(32)
        output_digest = sha256_hex(output_bytes)
        output_relative = _relative_path(target, restore_binding_output_object_path(target, output_digest))
        evidence = _build_restore_evidence(
            transaction_id=transaction_id,
            source=source,
            target=target,
            project_id=expected_project_id,
            store_identity=expected_store_identity,
            manifest=rebound,
            manifest_bytes=intended_manifest,
            receipt_hash=expected_restore_receipt_hash,
            source_snapshot=source_snapshot,
            source_snapshot_hash=expected_source_snapshot_hash,
            output_bytes=output_bytes,
            output_relative=output_relative,
            actor_id=actor_id,
            authority_grant_id=authority_grant_id,
            code_roots=code_values,
            schema_root=str(schema),
        )
        intended_evidence = canonical_bytes(evidence)
        record = _build_restore_transaction(
            transaction_id=transaction_id,
            source=source,
            target=target,
            project_id=expected_project_id,
            store_identity=expected_store_identity,
            receipt_hash=expected_restore_receipt_hash,
            actor_id=actor_id,
            authority_grant_id=authority_grant_id,
            source_snapshot=source_snapshot,
            source_snapshot_hash=expected_source_snapshot_hash,
            code_roots=code_values,
            schema_root=str(schema),
            original_manifest=original_manifest,
            intended_manifest=intended_manifest,
            original_evidence=None,
            intended_evidence=intended_evidence,
            output_bytes=output_bytes,
        )
        _validate_restore_binding_transaction(target, record, canonical_bytes(record))
        if source_snapshot_validator is not None:
            source_snapshot_validator()
        record, record_raw = _write_initial_transaction(target, record)
    else:
        if record_raw is None:
            raise IntegrityError("restore binding transaction bytes are missing")
        _validate_record_inputs(
            record,
            source=source,
            target=target,
            project_id=expected_project_id,
            store_identity=expected_store_identity,
            receipt_hash=expected_restore_receipt_hash,
            actor_id=actor_id,
            authority_grant_id=authority_grant_id,
            source_snapshot_hash=expected_source_snapshot_hash,
            code_roots=code_values,
            schema_root=str(schema),
            output_bytes=output_bytes,
        )
        if record["source_snapshot"] != source_snapshot:
            raise ConflictError("restore source snapshot changed")
        if expected_target_manifest_bytes_sha256 is not None and expected_target_manifest_bytes_sha256 not in {
            record["original_manifest_sha256"],
            record["intended_manifest_sha256"],
        }:
            raise ConflictError("target manifest pre-state changed")
        if source_snapshot_validator is not None:
            source_snapshot_validator()
        if record["state"] == "cleared":
            _require_cleared_without_temporaries(target, record)
            _validate_restore_join(target, record)
            if finalization_validator is not None:
                finalization_validator()
            validate_physical_roots(record)
            return _validate_restore_join(target, record)
        _cleanup_current_transaction_temporary(target, record, record_raw)

    if record_raw is None:
        raise IntegrityError("restore binding transaction bytes are missing")
    validate_physical_roots(record)

    if record["state"] == "prepared":
        if _RESTORE_STEPS.index(record["last_completed_durability_step"]) < _RESTORE_STEPS.index(
            "output-object-durable"
        ):
            _publish_output_object(target, record)
            record, record_raw = _transition_transaction(
                target,
                record,
                record_raw,
                state="prepared",
                durability_step="output-object-durable",
            )
        original_manifest = _from_hex(record["original_manifest_bytes"], "original_manifest_bytes")
        intended_manifest = _from_hex(record["intended_manifest_bytes"], "intended_manifest_bytes")
        if original_manifest is None or intended_manifest is None:
            raise IntegrityError("restore binding manifest bytes are incomplete")
        if _RESTORE_STEPS.index(record["last_completed_durability_step"]) < _RESTORE_STEPS.index("manifest-durable"):

            def validate_manifest_mutation() -> None:
                if source_snapshot_validator is not None:
                    source_snapshot_validator()
                validate_physical_roots(record)

            _publish_mutable_object(
                target,
                record,
                name="manifest",
                path=manifest_path,
                original=original_manifest,
                intended=intended_manifest,
                mutation_validator=validate_manifest_mutation,
            )
            record, record_raw = _transition_transaction(
                target,
                record,
                record_raw,
                state="prepared",
                durability_step="manifest-durable",
            )
        original_evidence = _from_hex(record["original_evidence_bytes"], "original_evidence_bytes")
        intended_evidence = _from_hex(record["intended_evidence_bytes"], "intended_evidence_bytes")
        if intended_evidence is None:
            raise IntegrityError("restore binding evidence bytes are incomplete")
        if _RESTORE_STEPS.index(record["last_completed_durability_step"]) < _RESTORE_STEPS.index("evidence-durable"):
            _publish_mutable_object(
                target,
                record,
                name="evidence",
                path=evidence_path,
                original=original_evidence,
                intended=intended_evidence,
            )
            record, record_raw = _transition_transaction(
                target,
                record,
                record_raw,
                state="prepared",
                durability_step="evidence-durable",
            )
        _validate_restore_join(target, record)
        record, record_raw = _transition_transaction(
            target,
            record,
            record_raw,
            state="published",
            durability_step="published-record-durable",
        )

    if record["state"] == "published":
        validate_physical_roots(record)
        if source_snapshot_validator is not None:
            source_snapshot_validator()
        _validate_restore_join(target, record)
        if finalization_validator is not None:
            finalization_validator()
        record, record_raw = _transition_transaction(
            target,
            record,
            record_raw,
            state="final_validated",
            durability_step="final-validation-durable",
        )

    if record["state"] == "final_validated":
        validate_physical_roots(record)
        _validate_restore_join(target, record)
        record, record_raw = _transition_transaction(
            target,
            record,
            record_raw,
            state="committed",
            durability_step="commit-durable",
        )

    if record["state"] == "committed":
        validate_physical_roots(record)
        _validate_restore_join(target, record)
        record, record_raw = _transition_transaction(
            target,
            record,
            record_raw,
            state="cleared",
            durability_step="clear-durable",
        )
        validate_physical_roots(record)
        return _validate_restore_join(target, record)
    raise IntegrityError(f"unsupported restore binding transaction state: {record['state']}")


def verify_restore_binding_admission(control_root: Path) -> dict[str, Any] | None:
    """Read-only admission for never-restored or durably cleared stores."""
    target = control_root.resolve(strict=True)
    _assert_no_second_restore_authority(target)
    record, _ = _read_restore_binding_transaction(target)
    evidence_raw = _file_bytes(_restore_binding_evidence_path(target))
    output_directory = target / "manifests" / _RESTORE_BINDING_OUTPUT_DIRECTORY
    outputs_exist = output_directory.exists() and any(output_directory.glob("sha256-*.json"))
    transition_temporaries = any((target / "manifests").glob(".restore-binding-transaction.*.tmp"))
    if record is None:
        if evidence_raw is not None or outputs_exist or transition_temporaries:
            raise IntegrityError("partial restore binding exists without a transaction record")
        return None
    if record["state"] != "cleared":
        raise IntegrityError(f"restore binding transaction state is not cleared: {record['state']}")
    _require_cleared_without_temporaries(target, record)
    _require_root_identity(target, record["target_root_identity"])
    _validate_restore_join(target, record)
    return record


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
