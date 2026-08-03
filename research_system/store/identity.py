from __future__ import annotations

import ctypes
import errno
import json
import os
import secrets
import stat
from dataclasses import dataclass, field as dataclass_field
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
_STORE_ORIGIN_NAME = "store-origin.json"
_RESTORE_BINDING_EVIDENCE_NAME = "restore-binding-evidence.json"
_RESTORE_BINDING_TRANSACTION_NAME = ".restore-binding-transaction.json"
_RESTORE_BINDING_OUTPUT_DIRECTORY = "restore-bindings"
_RESTORE_APPROVAL_PREFIX = "approval-sha256-"
_ORIGIN_WITNESS_DIRECTORY = "store-origins"
_ORIGIN_WITNESS_SCHEMA_ID = "ars://internal/store-origin-witness"
_ORIGIN_WITNESS_SCHEMA_VERSION = "1.0.0"
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


@dataclass(frozen=True, slots=True)
class StoreOriginWitness:
    """Externally retained, write-once authority for one initialized store."""

    schema_id: str
    schema_version: str
    project_id: str
    store_identity: str
    initial_control_root: str
    initial_physical_root_identity: dict[str, str]
    initial_manifest: dict[str, Any]
    initial_manifest_sha256: str
    _raw_bytes: bytes = dataclass_field(repr=False, compare=False)

    @property
    def slot(self) -> str:
        return sha256_hex(
            canonical_bytes(
                {
                    "project_id": self.project_id,
                    "initial_control_root": self.initial_control_root,
                }
            )
        )

    @property
    def raw_bytes(self) -> bytes:
        return self._raw_bytes

    @property
    def raw_sha256(self) -> str:
        return sha256_hex(self._raw_bytes)

    @property
    def path_name(self) -> str:
        return f"sha256-{self.slot}.json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "store_identity": self.store_identity,
            "initial_control_root": self.initial_control_root,
            "initial_physical_root_identity": dict(self.initial_physical_root_identity),
            "initial_manifest": self.initial_manifest,
            "initial_manifest_sha256": self.initial_manifest_sha256,
        }

    @classmethod
    def from_raw(cls, raw: bytes, *, expected_sha256: str | None = None) -> "StoreOriginWitness":
        if expected_sha256 is not None and sha256_hex(raw) != expected_sha256:
            raise IntegrityError("origin witness raw bytes differ from foundation pin")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("origin witness is invalid") from exc
        if not isinstance(value, dict):
            raise IntegrityError("origin witness is invalid")
        required = {
            "schema_id",
            "schema_version",
            "project_id",
            "store_identity",
            "initial_control_root",
            "initial_physical_root_identity",
            "initial_manifest",
            "initial_manifest_sha256",
        }
        if set(value) != required or raw != canonical_bytes(value):
            raise IntegrityError("origin witness fields are invalid")
        if value["schema_id"] != _ORIGIN_WITNESS_SCHEMA_ID or value["schema_version"] != _ORIGIN_WITNESS_SCHEMA_VERSION:
            raise IntegrityError("origin witness schema is unsupported")
        project_id = validate_id(str(value["project_id"]), "project")
        identity = value["store_identity"]
        if not _is_sha256(identity):
            raise IntegrityError("origin witness store identity is invalid")
        initial_root = value["initial_control_root"]
        if not isinstance(initial_root, str) or not Path(initial_root).is_absolute():
            raise IntegrityError("origin witness initial root is invalid")
        physical = value["initial_physical_root_identity"]
        if (
            not isinstance(physical, dict)
            or set(physical) != {"device", "inode"}
            or any(not isinstance(item, str) or not item.isdecimal() for item in physical.values())
        ):
            raise IntegrityError("origin witness physical root identity is invalid")
        manifest = value["initial_manifest"]
        if not isinstance(manifest, dict):
            raise IntegrityError("origin witness initial manifest is invalid")
        manifest_raw_hash = value["initial_manifest_sha256"]
        if not _is_sha256(manifest_raw_hash):
            raise IntegrityError("origin witness manifest hash is invalid")
        if manifest_raw_hash != sha256_hex(canonical_bytes(manifest)):
            raise IntegrityError("origin witness manifest hash does not match manifest")
        if (
            manifest.get("project_id") != project_id
            or manifest.get("store_identity") != identity
            or manifest.get("control_root") != initial_root
        ):
            raise IntegrityError("origin witness manifest binding mismatch")
        witness = cls(
            _ORIGIN_WITNESS_SCHEMA_ID,
            _ORIGIN_WITNESS_SCHEMA_VERSION,
            project_id,
            identity,
            initial_root,
            {key: str(item) for key, item in physical.items()},
            manifest,
            manifest_raw_hash,
            raw,
        )
        if witness.path_name != f"sha256-{witness.slot}.json":
            raise IntegrityError("origin witness locator is invalid")
        return witness


class InitializedStore(str):
    """String-compatible initialization result carrying its external witness."""

    witness: StoreOriginWitness
    manifest: dict[str, Any]
    _witness_path: Path

    def __new__(
        cls,
        store_identity: str,
        manifest: dict[str, Any],
        witness: StoreOriginWitness,
        witness_path: Path,
    ):
        value = super().__new__(cls, store_identity)
        value.witness = witness
        value.manifest = manifest
        value._witness_path = witness_path
        return value

    @property
    def store_identity(self) -> str:
        return str(self)

    @property
    def witness_path(self) -> Path:
        return self._witness_path


def origin_witness_path(
    origin_authority_root: Path,
    *,
    project_id: str,
    initial_control_root: Path,
) -> Path:
    """Return the canonical external locator for one project/root slot."""
    project = validate_id(project_id, "project")
    initial_root = str(initial_control_root.resolve(strict=False))
    slot = sha256_hex(canonical_bytes({"project_id": project, "initial_control_root": initial_root}))
    return origin_authority_root.resolve(strict=False) / _ORIGIN_WITNESS_DIRECTORY / f"sha256-{slot}.json"


def _require_physical_path(path: Path, *, require_exists: bool) -> Path:
    """Resolve a path only after rejecting symlink/reparse components."""
    candidate = Path(os.path.abspath(os.fspath(path)))
    if not candidate.is_absolute() or not candidate.anchor:
        raise IntegrityError("physical path must be absolute")
    anchor = Path(candidate.anchor)
    current = anchor
    parts = candidate.relative_to(anchor).parts
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            if require_exists:
                raise IntegrityError(f"physical path is unavailable: {current}") from exc
            break
        except OSError as exc:
            raise IntegrityError(f"physical path identity is unavailable: {current}") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
            raise IntegrityError(f"physical path has a reparse component: {current}")
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise IntegrityError(f"physical path ancestor is not a directory: {current}")
    try:
        return candidate.resolve(strict=require_exists)
    except (FileNotFoundError, OSError) as exc:
        raise IntegrityError(f"physical path is unavailable: {candidate}") from exc


def _validate_origin_witness_locator(
    path: Path,
    *,
    expected_witness: StoreOriginWitness | None = None,
    require_exists: bool,
) -> Path:
    """Validate the complete external witness locator without following escapes."""
    resolved = _require_physical_path(path, require_exists=require_exists)
    if resolved.parent.name != _ORIGIN_WITNESS_DIRECTORY:
        raise IntegrityError("approved origin witness locator is not canonical")
    if require_exists and not resolved.is_file():
        raise IntegrityError("approved origin witness locator is not a regular file")
    origin_root = _require_physical_path(resolved.parent.parent, require_exists=True)
    if expected_witness is not None:
        expected = origin_witness_path(
            origin_root,
            project_id=expected_witness.project_id,
            initial_control_root=Path(expected_witness.initial_control_root),
        ).resolve(strict=False)
        if resolved != expected or resolved.name != expected_witness.path_name:
            raise IntegrityError("approved origin witness locator differs from its canonical slot")
    return resolved


def _require_physical_disjoint(left: Path, right: Path, *, message: str) -> None:
    """Reject equal, nested, or physically aliased directory roots."""
    left_resolved = _require_physical_path(left, require_exists=True)
    right_resolved = _require_physical_path(right, require_exists=True)
    if (
        left_resolved == right_resolved
        or left_resolved in right_resolved.parents
        or right_resolved in left_resolved.parents
    ):
        raise ConflictError(message)
    try:
        if os.path.samefile(left_resolved, right_resolved):
            raise ConflictError(message)
    except FileNotFoundError as exc:
        raise ConflictError(message) from exc


def _validate_origin_authority_root(
    origin_authority_root: Path,
    *,
    code_roots: list[Path],
    control_roots: list[Path],
) -> Path:
    try:
        root = _require_physical_path(origin_authority_root, require_exists=True)
    except (IntegrityError, OSError) as exc:
        raise ArsError("origin authority root must be an existing directory and physical") from exc
    if not root.is_dir():
        raise ArsError("origin authority root must be an existing directory and physical")
    try:
        metadata = root.lstat()
    except OSError as exc:
        raise ArsError("origin authority root identity is unavailable") from exc
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
        raise ArsError("origin authority root must be a physical directory")
    candidates = [root_path.resolve(strict=True) for root_path in code_roots]
    candidates.extend(root_path.resolve(strict=False) for root_path in control_roots)
    if any(root == candidate or root in candidate.parents or candidate in root.parents for candidate in candidates):
        raise ArsError("origin authority root must be physically disjoint from every store/code root")
    return root


def build_store_origin_witness(
    manifest: dict[str, Any],
    *,
    initial_control_root: Path,
    physical_root: Path | None = None,
) -> StoreOriginWitness:
    """Build a witness from the immutable initialization inputs."""
    initial_root = str(initial_control_root.resolve(strict=False))
    raw_manifest = canonical_bytes(manifest)
    value = {
        "schema_id": _ORIGIN_WITNESS_SCHEMA_ID,
        "schema_version": _ORIGIN_WITNESS_SCHEMA_VERSION,
        "project_id": validate_id(str(manifest.get("project_id")), "project"),
        "store_identity": str(manifest.get("store_identity")),
        "initial_control_root": initial_root,
        "initial_physical_root_identity": _physical_root_identity(physical_root or initial_control_root),
        "initial_manifest": manifest,
        "initial_manifest_sha256": sha256_hex(raw_manifest),
    }
    return StoreOriginWitness.from_raw(canonical_bytes(value))


def persist_store_origin_witness(
    witness: StoreOriginWitness,
    origin_authority_root: Path,
    *,
    expected_sha256: str | None = None,
) -> Path:
    """Write one external witness once and reject all conflicting rewrites."""
    root = _validate_origin_authority_root(
        origin_authority_root,
        code_roots=[Path(str(item)) for item in witness.initial_manifest.get("code_roots", [])],
        control_roots=[Path(witness.initial_control_root)],
    )
    path = origin_witness_path(
        root,
        project_id=witness.project_id,
        initial_control_root=Path(witness.initial_control_root),
    )
    _validate_origin_witness_locator(path, expected_witness=witness, require_exists=False)
    data = witness.raw_bytes
    if expected_sha256 is not None and sha256_hex(data) != expected_sha256:
        raise IntegrityError("origin witness raw bytes differ from foundation pin")
    path.parent.mkdir(parents=True, exist_ok=True)
    _validate_origin_witness_locator(path, expected_witness=witness, require_exists=False)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        existing = _file_bytes(path)
        if existing != data:
            raise ConflictError("origin witness conflicts with existing authority")
        StoreOriginWitness.from_raw(existing or b"", expected_sha256=expected_sha256)
    else:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    if not _fsync_directory(path.parent):
        raise ArsError("origin witness requires directory durability")
    return path


def load_store_origin_witness(path: Path, *, expected_sha256: str) -> StoreOriginWitness:
    """Load the foundation-pinned witness bytes; local store state is ignored."""
    path = _validate_origin_witness_locator(path, require_exists=True)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise IntegrityError("approved origin witness is unavailable") from exc
    witness = StoreOriginWitness.from_raw(raw, expected_sha256=expected_sha256)
    expected_name = f"sha256-{witness.slot}.json"
    if path.name != expected_name or path.parent.name != _ORIGIN_WITNESS_DIRECTORY:
        raise IntegrityError("approved origin witness locator is not canonical")
    return witness


def _validate_approved_origin_witness_path(
    path: Path | None,
    witness: StoreOriginWitness,
) -> tuple[Path, Path]:
    """Validate the owner/foundation-supplied witness path and its raw bytes."""
    if path is None or not isinstance(path, Path) or not path.is_absolute():
        raise IntegrityError("foundation-approved origin witness path is required")
    resolved = _validate_origin_witness_locator(path, expected_witness=witness, require_exists=True)
    loaded = load_store_origin_witness(resolved, expected_sha256=witness.raw_sha256)
    if loaded.raw_bytes != witness.raw_bytes:
        raise IntegrityError("foundation-approved origin witness bytes changed")
    return resolved, resolved.parent.parent


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


def _restored_manifest_hash(manifest: dict[str, Any], approval_sha256: str) -> str:
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    return sha256_hex(
        canonical_bytes(
            {
                "schema_id": "ars://internal/restored-store-manifest",
                "schema_version": "1.0.0",
                "approval_sha256": approval_sha256,
                "manifest": unsigned,
            }
        )
    )


def _read_manifest(
    path: Path,
    *,
    require_canonical: bool,
    restore_approval_sha256: str | None = None,
) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"invalid store identity manifest: {path}") from exc
    if not isinstance(value, dict):
        raise IntegrityError(f"invalid store identity manifest: {path}")
    if require_canonical and raw != canonical_bytes(value):
        raise IntegrityError("store identity manifest is noncanonical")
    expected_hash = (
        _manifest_hash(value)
        if restore_approval_sha256 is None
        else _restored_manifest_hash(value, restore_approval_sha256)
    )
    if value.get("manifest_hash") != expected_hash:
        raise IntegrityError("store identity manifest hash mismatch")
    return value


_STORE_ORIGIN_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "initial_control_root",
        "project_id",
        "store_identity",
        "initial_identity_sha256",
        "origin_sha256",
    }
)


def _store_origin_value(manifest: dict[str, Any], initial_control_root: Path) -> dict[str, str]:
    stable = {
        "schema_id": manifest.get("schema_id"),
        "schema_version": manifest.get("schema_version"),
        "initial_control_root": str(initial_control_root.resolve(strict=False)),
        "project_id": manifest.get("project_id"),
        "store_identity": manifest.get("store_identity"),
    }
    value = {
        "schema_id": "ars://internal/store-origin",
        "schema_version": "1.0.0",
        "initial_control_root": stable["initial_control_root"],
        "project_id": str(stable["project_id"]),
        "store_identity": str(stable["store_identity"]),
        "initial_identity_sha256": sha256_hex(canonical_bytes(stable)),
    }
    value["origin_sha256"] = sha256_hex(canonical_bytes(value))
    return value


def write_store_origin(
    store_root: Path,
    manifest: dict[str, Any],
    *,
    initial_control_root: Path | None = None,
) -> None:
    """Create the immutable initialized-store origin discriminator."""
    root = store_root.resolve(strict=False)
    origin_root = initial_control_root or Path(str(manifest.get("control_root", "")))
    value = _store_origin_value(manifest, origin_root)
    data = canonical_bytes(value)
    path = root / "manifests" / _STORE_ORIGIN_NAME
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if _file_bytes(path) != data:
            raise ConflictError("store origin provenance conflicts")
        return
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if not _fsync_directory(path.parent):
        raise ArsError("store origin provenance requires directory durability")


def _read_store_origin(control_root: Path) -> dict[str, str]:
    path = control_root / "manifests" / _STORE_ORIGIN_NAME
    raw = _file_bytes(path)
    if raw is None:
        raise IntegrityError("store origin provenance is missing")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("store origin provenance is invalid") from exc
    if not isinstance(value, dict) or set(value) != _STORE_ORIGIN_FIELDS or raw != canonical_bytes(value):
        raise IntegrityError("store origin provenance fields are invalid")
    unsigned = {key: item for key, item in value.items() if key != "origin_sha256"}
    if (
        value.get("schema_id") != "ars://internal/store-origin"
        or value.get("schema_version") != "1.0.0"
        or value.get("origin_sha256") != sha256_hex(canonical_bytes(unsigned))
        or not isinstance(value.get("initial_control_root"), str)
        or not Path(str(value["initial_control_root"])).is_absolute()
        or not _is_sha256(value.get("store_identity"))
        or not _is_sha256(value.get("initial_identity_sha256"))
    ):
        raise IntegrityError("store origin provenance values are invalid")
    return {key: str(item) for key, item in value.items()}


def _validate_store_origin(
    control_root: Path,
    manifest: dict[str, Any],
    *,
    expected_initial_root: Path,
) -> dict[str, str]:
    origin = _read_store_origin(control_root)
    stable = {
        "schema_id": manifest.get("schema_id"),
        "schema_version": manifest.get("schema_version"),
        "initial_control_root": origin["initial_control_root"],
        "project_id": manifest.get("project_id"),
        "store_identity": manifest.get("store_identity"),
    }
    if (
        Path(origin["initial_control_root"]).resolve(strict=False) != expected_initial_root.resolve(strict=False)
        or origin["project_id"] != manifest.get("project_id")
        or origin["store_identity"] != manifest.get("store_identity")
        or origin["initial_identity_sha256"] != sha256_hex(canonical_bytes(stable))
    ):
        raise IntegrityError("store origin provenance binding mismatch")
    return origin


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
    try:
        manifest = _read_manifest(_manifest_path(control), require_canonical=True)
    except IntegrityError as ordinary_error:
        record, _ = _read_restore_binding_transaction(control)
        if record is None:
            raise ordinary_error
        manifest = _read_manifest(
            _manifest_path(control),
            require_canonical=True,
            restore_approval_sha256=str(record["approval_sha256"]),
        )
    _validate_manifest_identity(manifest)
    return manifest


def _validate_external_witness_for_store(
    control_root: Path,
    manifest: dict[str, Any],
    witness: StoreOriginWitness,
) -> None:
    """Bind a live store to foundation-supplied witness bytes."""
    control = control_root.resolve(strict=True)
    if manifest.get("project_id") != witness.project_id or manifest.get("store_identity") != witness.store_identity:
        raise IntegrityError("store identity differs from approved origin witness")
    record, _ = _read_restore_binding_transaction(control)
    if record is None:
        if manifest.get("control_root") != witness.initial_control_root:
            raise IntegrityError("store root differs from approved origin witness")
        if _physical_root_identity(control) != witness.initial_physical_root_identity:
            raise IntegrityError("store physical root identity differs from approved origin witness")
        if sha256_hex(canonical_bytes(manifest)) != witness.initial_manifest_sha256:
            raise IntegrityError("initial store manifest differs from approved origin witness")
        return
    if record.get("origin_witness_sha256") != witness.raw_sha256:
        raise IntegrityError("restore transaction origin witness differs from approved witness")
    if record.get("source_root") != witness.initial_control_root:
        raise IntegrityError("restore source lineage differs from approved origin witness")
    if record.get("source_root_identity") != witness.initial_physical_root_identity:
        raise IntegrityError("restore source physical identity differs from approved origin witness")
    if manifest.get("origin_witness_sha256") != witness.raw_sha256:
        raise IntegrityError("restored manifest origin witness differs from approved witness")
    if manifest.get("origin_witness_path") != record.get("origin_witness_path"):
        raise IntegrityError("restored manifest origin witness path differs from transaction")


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
    *,
    origin_authority_root: Path | None = None,
    approved_origin_witness_sha256: str | None = None,
) -> InitializedStore:
    project_id = validate_id(project_id, "project")
    if origin_authority_root is None:
        raise ArsError("origin authority root is required for new stores")
    requested_control = control_root.resolve(strict=False)
    origin_root = _validate_origin_authority_root(
        origin_authority_root,
        code_roots=code_roots,
        control_roots=[requested_control],
    )
    control = require_external_control_root(code_roots, requested_control)
    manifest_path = _manifest_path(control)
    witness_path = origin_witness_path(
        origin_root,
        project_id=project_id,
        initial_control_root=control,
    )
    witness: StoreOriginWitness | None = None
    if witness_path.exists():
        try:
            witness_raw = witness_path.read_bytes()
        except OSError as exc:
            raise IntegrityError("origin witness reservation is unavailable") from exc
        witness = load_store_origin_witness(
            witness_path,
            expected_sha256=approved_origin_witness_sha256 or sha256_hex(witness_raw),
        )
        if not _fsync_directory(witness_path.parent):
            raise ArsError("origin witness reservation requires directory durability")
    if manifest_path.exists():
        if witness is None:
            raise ConflictError("existing control store has no independent origin witness")
        manifest = _read_manifest(manifest_path, require_canonical=True)
        if (
            witness.initial_control_root != str(control)
            or sha256_hex(canonical_bytes(manifest)) != witness.initial_manifest_sha256
            or manifest != witness.initial_manifest
        ):
            raise ConflictError("control store conflicts with its origin witness")
    else:
        if witness is None:
            resolved_codes = sorted(str(root.resolve(strict=True)) for root in code_roots)
            manifest = {
                "schema_id": "ars://core/store-identity",
                "schema_version": "1.0.0",
                "project_id": project_id,
                "store_identity": secrets.token_hex(32),
                "control_root": str(control),
                "code_roots": resolved_codes,
                "endpoint_scheme": "local-cli",
            }
            manifest["manifest_hash"] = _manifest_hash(manifest)
            witness = build_store_origin_witness(manifest, initial_control_root=control)
            witness_path = persist_store_origin_witness(
                witness,
                origin_root,
                expected_sha256=approved_origin_witness_sha256,
            )
        else:
            manifest = dict(witness.initial_manifest)
            if (
                witness.initial_control_root != str(control)
                or _physical_root_identity(control) != witness.initial_physical_root_identity
            ):
                raise ConflictError("reserved origin witness does not match the control root")
        try:
            descriptor = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ConflictError(f"control store initialization reservation changed: {control}") from exc
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_bytes(manifest))
            handle.flush()
            os.fsync(handle.fileno())
    if witness is None:  # pragma: no cover - all paths create or load the reservation above
        raise IntegrityError("control store origin witness is unavailable")
    write_store_origin(control, manifest)
    return InitializedStore(str(manifest["store_identity"]), manifest, witness, witness_path)


def load_store_manifest(
    control_root: Path,
    *,
    approved_witness: StoreOriginWitness | None = None,
    approved_witness_path: Path | None = None,
) -> dict[str, Any]:
    if approved_witness is None:
        raise IntegrityError("approved origin witness is required")
    control = control_root.resolve(strict=True)
    manifest = load_store_manifest_unbound(control)
    if manifest.get("control_root") != str(control):
        raise IntegrityError("store control-root binding mismatch")
    _validate_external_witness_for_store(control, manifest, approved_witness)
    verify_restore_binding_admission(
        control,
        approved_witness=approved_witness,
        approved_witness_path=approved_witness_path,
    )
    return manifest


def _fsync_directory(path: Path) -> bool:
    """Attempt directory-entry durability and report unsupported platforms honestly."""
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        flush_file_buffers = kernel32.FlushFileBuffers
        flush_file_buffers.argtypes = [ctypes.c_void_p]
        flush_file_buffers.restype = ctypes.c_int
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        handle = create_file(
            str(path.resolve(strict=True)),
            0x40000000,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle in {None, invalid_handle}:
            error = ctypes.get_last_error()
            if error in {1, 5, 50, 87}:
                return False
            raise ctypes.WinError(error)
        try:
            if not flush_file_buffers(handle):
                error = ctypes.get_last_error()
                if error in {1, 5, 50, 87}:
                    return False
                raise ctypes.WinError(error)
        finally:
            close_handle(handle)
        return True
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


def restore_binding_approval_object_path(control_root: Path, digest: str) -> Path:
    if not _is_sha256(digest):
        raise IntegrityError("restore approval digest is invalid")
    return control_root / "manifests" / _RESTORE_BINDING_OUTPUT_DIRECTORY / f"{_RESTORE_APPROVAL_PREFIX}{digest}.json"


def _relative_path(target: Path, path: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError as exc:
        raise IntegrityError("restore binding path escapes the target store") from exc


def _record_path(target: Path, relative: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise IntegrityError("restore binding relative path is invalid")
    path = target.joinpath(*relative.split("/"))
    try:
        path.relative_to(target)
    except ValueError as exc:
        raise IntegrityError("restore binding path escapes the target store") from exc
    _require_physical_restore_path(target, path)
    return path


def _require_physical_restore_path(target: Path, path: Path) -> None:
    """Reject every symlink, junction, or reparse component below the physical root."""
    root = target.resolve(strict=True)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise IntegrityError("restore binding path escapes the target store") from exc
    current = root
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise IntegrityError(f"restore binding physical path is unavailable: {current}") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
            raise IntegrityError(f"restore binding path has a reparse ancestor: {current}")
        if current != path and not stat.S_ISDIR(metadata.st_mode):
            raise IntegrityError(f"restore binding path ancestor is not a directory: {current}")
        try:
            resolved = current.resolve(strict=True)
            if resolved.parent != current.parent.resolve(strict=True) or not os.path.samefile(
                current.parent,
                resolved.parent,
            ):
                raise IntegrityError(f"restore binding path ancestor is not physically bound: {current}")
        except IntegrityError:
            raise
        except OSError as exc:
            raise IntegrityError(f"restore binding physical identity is unavailable: {current}") from exc


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


_RESTORE_PREFLIGHT_FIELDS = frozenset(
    {
        "status",
        "failed_predicates",
        "receipt_hash",
        "ledger_hash",
        "snapshot_hash",
        "target_endpoint_ownership_hash",
        "artefact_manifest_hash",
        "availability_observations_hash",
        "registry_hash",
        "target_root",
        "project_id",
        "store_identity",
        "tail_position",
        "tail_hash",
        "snapshot_id",
        "actor_id",
        "authority_grant_id",
        "result_hash",
        "source_root",
        "code_roots",
        "schema_root",
        "source_snapshot_hash",
        "target_manifest_bytes_sha256",
        "expected_output_sha256",
        "origin_witness_path",
        "origin_witness_sha256",
        "origin_initial_control_root",
        "origin_initial_physical_root_identity",
    }
)
_RESTORE_APPROVAL_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "restore_preflight",
        "source_root_identity",
        "target_root_identity",
        "source_snapshot",
        "original_manifest_sha256",
        "rebound_manifest",
        "origin_witness_path",
        "origin_witness_sha256",
        "origin_initial_control_root",
        "origin_initial_physical_root_identity",
    }
)


def _validate_preflight_approval(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _RESTORE_PREFLIGHT_FIELDS:
        raise IntegrityError("restore approval preflight fields are invalid")
    value = dict(value)
    if isinstance(value.get("failed_predicates"), tuple):
        value["failed_predicates"] = list(value["failed_predicates"])
    if isinstance(value.get("code_roots"), tuple):
        value["code_roots"] = list(value["code_roots"])
    expected = dict(value)
    expected["result_hash"] = ""
    digest_fields = (
        "receipt_hash",
        "ledger_hash",
        "snapshot_hash",
        "target_endpoint_ownership_hash",
        "artefact_manifest_hash",
        "availability_observations_hash",
        "registry_hash",
        "store_identity",
        "tail_hash",
        "result_hash",
        "source_snapshot_hash",
        "target_manifest_bytes_sha256",
        "expected_output_sha256",
        "origin_witness_sha256",
    )
    if (
        value.get("status") != "verified"
        or value.get("failed_predicates") != []
        or any(not _is_sha256(value.get(field)) for field in digest_fields)
        or value.get("result_hash") != sha256_hex(canonical_bytes(expected))
        or not isinstance(value.get("code_roots"), list)
        or not value["code_roots"]
        or any(not isinstance(root, str) or not Path(root).is_absolute() for root in value["code_roots"])
        or not isinstance(value.get("schema_root"), str)
        or not Path(value["schema_root"]).is_absolute()
        or not isinstance(value.get("origin_witness_path"), str)
        or not Path(value["origin_witness_path"]).is_absolute()
        or not isinstance(value.get("origin_initial_control_root"), str)
        or not Path(value["origin_initial_control_root"]).is_absolute()
        or not isinstance(value.get("origin_initial_physical_root_identity"), dict)
        or set(value["origin_initial_physical_root_identity"]) != {"device", "inode"}
        or any(
            not isinstance(item, str) or not item.isdecimal()
            for item in value["origin_initial_physical_root_identity"].values()
        )
    ):
        raise IntegrityError("restore approval preflight values are invalid")
    return value


def _build_restore_approval(
    *,
    restore_preflight: dict[str, Any],
    source: Path,
    target: Path,
    source_snapshot: dict[str, Any],
    original_manifest: bytes,
    rebound_manifest: dict[str, Any],
) -> dict[str, Any]:
    unsigned_rebound = {key: item for key, item in rebound_manifest.items() if key != "manifest_hash"}
    return {
        "schema_id": "ars://internal/restore-binding-approval",
        "schema_version": "1.0.0",
        "restore_preflight": restore_preflight,
        "source_root_identity": _physical_root_identity(source),
        "target_root_identity": _physical_root_identity(target),
        "source_snapshot": source_snapshot,
        "original_manifest_sha256": sha256_hex(original_manifest),
        "rebound_manifest": unsigned_rebound,
        "origin_witness_path": restore_preflight["origin_witness_path"],
        "origin_witness_sha256": restore_preflight["origin_witness_sha256"],
        "origin_initial_control_root": restore_preflight["origin_initial_control_root"],
        "origin_initial_physical_root_identity": restore_preflight["origin_initial_physical_root_identity"],
    }


def _validate_restore_approval(target: Path, value: dict[str, Any], raw: bytes) -> None:
    if raw != canonical_bytes(value) or set(value) != _RESTORE_APPROVAL_FIELDS:
        raise IntegrityError("restore approval fields are invalid")
    if (
        value.get("schema_id") != "ars://internal/restore-binding-approval"
        or value.get("schema_version") != "1.0.0"
        or not isinstance(value.get("source_snapshot"), dict)
        or not _is_sha256(value.get("original_manifest_sha256"))
        or not isinstance(value.get("rebound_manifest"), dict)
        or "manifest_hash" in value["rebound_manifest"]
    ):
        raise IntegrityError("restore approval values are invalid")
    preflight = _validate_preflight_approval(value["restore_preflight"])
    if Path(str(preflight["target_root"])).resolve(strict=False) != target:
        raise IntegrityError("restore approval target binding is invalid")
    if sha256_hex(canonical_bytes(value["source_snapshot"])) != preflight["source_snapshot_hash"]:
        raise IntegrityError("restore approval source snapshot is invalid")
    for field in (
        "origin_witness_path",
        "origin_witness_sha256",
        "origin_initial_control_root",
        "origin_initial_physical_root_identity",
    ):
        if value[field] != preflight[field]:
            raise IntegrityError(f"restore approval origin witness join is invalid: {field}")
    for identity_field in ("source_root_identity", "target_root_identity"):
        identity = value[identity_field]
        if (
            not isinstance(identity, dict)
            or set(identity) != {"device", "inode"}
            or any(not isinstance(item, str) or not item.isdecimal() for item in identity.values())
        ):
            raise IntegrityError(f"restore approval root identity is invalid: {identity_field}")
    rebound = value["rebound_manifest"]
    if (
        rebound.get("control_root") != str(target)
        or rebound.get("project_id") != preflight["project_id"]
        or rebound.get("store_identity") != preflight["store_identity"]
        or rebound.get("code_roots") != preflight["code_roots"]
        or rebound.get("schema_root") != preflight["schema_root"]
    ):
        raise IntegrityError("restore approval rebound manifest is invalid")
    output = canonical_restore_binding_output(
        target,
        str(preflight["project_id"]),
        str(preflight["store_identity"]),
        [Path(root) for root in preflight["code_roots"]],
        Path(str(preflight["schema_root"])),
    )
    if sha256_hex(output) != preflight["expected_output_sha256"]:
        raise IntegrityError("restore approval canonical output is invalid")


def _read_restore_approval(target: Path, digest: str) -> tuple[dict[str, Any], bytes]:
    output_directory = target / "manifests" / _RESTORE_BINDING_OUTPUT_DIRECTORY
    _require_physical_restore_path(target, output_directory)
    candidates = set(output_directory.glob(f"{_RESTORE_APPROVAL_PREFIX}*.json")) if output_directory.exists() else set()
    expected_path = restore_binding_approval_object_path(target, digest)
    if candidates != {expected_path}:
        raise IntegrityError("restore approval exact-set closure is invalid")
    raw = _file_bytes(expected_path)
    if raw is None or sha256_hex(raw) != digest:
        raise IntegrityError("restore approval object is missing or invalid")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("restore approval object is invalid") from exc
    if not isinstance(value, dict):
        raise IntegrityError("restore approval object is invalid")
    _validate_restore_approval(target, value, raw)
    return value, raw


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
        "approval_object_path",
        "approval_sha256",
        "restore_preflight_result_hash",
        "output_object_path",
        "output_object_sha256",
        "actor_id",
        "authority_grant_id",
        "code_roots",
        "schema_root",
        "source_root_identity",
        "origin_witness_path",
        "origin_witness_sha256",
        "origin_initial_control_root",
        "origin_initial_physical_root_identity",
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
        or not isinstance(value["origin_witness_path"], str)
        or not Path(value["origin_witness_path"]).is_absolute()
        or not _is_sha256(value["origin_witness_sha256"])
        or not isinstance(value["origin_initial_control_root"], str)
        or not Path(value["origin_initial_control_root"]).is_absolute()
        or value["source_root"] != value["origin_initial_control_root"]
        or value["source_root_identity"] != value["origin_initial_physical_root_identity"]
    ):
        raise IntegrityError("restore binding evidence values are invalid")
    for field in (
        "manifest_hash",
        "receipt_hash",
        "source_snapshot_hash",
        "expected_output_sha256",
        "target_manifest_bytes_sha256",
        "output_object_sha256",
        "approval_sha256",
        "restore_preflight_result_hash",
        "origin_witness_sha256",
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
    approval = _record_path(target, str(value["approval_object_path"]))
    if approval != restore_binding_approval_object_path(target, str(value["approval_sha256"])):
        raise IntegrityError("restore binding evidence approval path is invalid")


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
        "approval_object_path",
        "approval_sha256",
        "restore_preflight_result_hash",
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
        "origin_witness_path",
        "origin_witness_sha256",
        "origin_initial_control_root",
        "origin_initial_physical_root_identity",
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
        or value["transaction_id"] != value["approval_sha256"]
        or not _is_sha256(value["restore_preflight_result_hash"])
        or not isinstance(value["origin_witness_path"], str)
        or not Path(value["origin_witness_path"]).is_absolute()
        or not _is_sha256(value["origin_witness_sha256"])
        or not isinstance(value["origin_initial_control_root"], str)
        or not Path(value["origin_initial_control_root"]).is_absolute()
        or not isinstance(value["origin_initial_physical_root_identity"], dict)
        or set(value["origin_initial_physical_root_identity"]) != {"device", "inode"}
        or any(
            not isinstance(item, str) or not item.isdecimal()
            for item in value["origin_initial_physical_root_identity"].values()
        )
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
        or str(source) != value["origin_initial_control_root"]
        or value["source_root_identity"] != value["origin_initial_physical_root_identity"]
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
    approval = _record_path(target, str(value["approval_object_path"]))
    if approval != restore_binding_approval_object_path(target, str(value["approval_sha256"])):
        raise IntegrityError("restore binding transaction approval path is invalid")
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
    transaction_path = restore_binding_transaction_path(target)
    raw = _file_bytes(transaction_path)
    if raw is None:
        return None, None
    manifests = transaction_path.parent
    if not _fsync_directory(manifests):
        raise ArsError("restore binding cannot trust an unconfirmed transaction generation")
    output_directory = manifests / _RESTORE_BINDING_OUTPUT_DIRECTORY
    if output_directory.exists():
        _require_physical_restore_path(target, output_directory)
        if not _fsync_directory(output_directory):
            raise ArsError("restore binding cannot trust unconfirmed restore objects")
    confirmed = _file_bytes(transaction_path)
    if confirmed != raw:
        raise ConflictError("restore binding transaction changed during durability confirmation")
    raw = confirmed
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


def _after_restore_owned_temporary_compared(path: Path) -> None:
    """Test seam while the compared temporary identity is handle-sealed."""


def _after_restore_initial_transaction_temporary_durable(path: Path) -> None:
    """Test seam after generation zero is durable but before canonical publication."""


def _transaction_transition_path(target: Path, transaction_id: str, generation: int) -> Path:
    return target / "manifests" / f".restore-binding-transaction.{transaction_id}.{generation}.tmp"


def _windows_file_identity(handle: int) -> tuple[int, bytes]:
    class FileId128(ctypes.Structure):
        _fields_ = [("identifier", ctypes.c_ubyte * 16)]

    class FileIdInfo(ctypes.Structure):
        _fields_ = [("volume_serial_number", ctypes.c_ulonglong), ("file_id", FileId128)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_information = kernel32.GetFileInformationByHandleEx
    get_information.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    get_information.restype = ctypes.c_int
    information = FileIdInfo()
    if not get_information(handle, 18, ctypes.byref(information), ctypes.sizeof(information)):
        raise ctypes.WinError(ctypes.get_last_error())
    return information.volume_serial_number, bytes(information.file_id.identifier)


def _windows_read_handle(handle: int) -> bytes:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_size = kernel32.GetFileSizeEx
    get_size.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_longlong)]
    get_size.restype = ctypes.c_int
    read_file = kernel32.ReadFile
    read_file.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
    ]
    read_file.restype = ctypes.c_int
    size = ctypes.c_longlong()
    if not get_size(handle, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    remaining = size.value
    chunks: list[bytes] = []
    while remaining:
        length = min(remaining, 1024 * 1024)
        buffer = ctypes.create_string_buffer(length)
        read = ctypes.c_uint32()
        if not read_file(handle, buffer, length, ctypes.byref(read), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if read.value == 0:
            raise OSError("restore binding temporary ended before its recorded size")
        chunks.append(buffer.raw[: read.value])
        remaining -= read.value
    return b"".join(chunks)


def _windows_open_file(path: Path, access: int, share: int) -> int:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    handle = create_file(str(path), access, share, None, 3, 0x00200000, None)
    invalid_handle = ctypes.c_void_p(-1).value
    if handle in {None, invalid_handle}:
        raise ctypes.WinError(ctypes.get_last_error())
    return int(handle)


def _windows_close_handle(handle: int) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_int
    if not close_handle(handle):
        raise ctypes.WinError(ctypes.get_last_error())


def _windows_delete_owned_temporary(path: Path, anchor: Path, expected: bytes) -> None:
    if os.name != "nt":
        raise ArsError("restore binding cannot seal temporary cleanup on this platform")
    temporary_handle = -1
    anchor_handle = -1
    try:
        # The narrow share mode prevents name replacement throughout compare/delete.
        temporary_handle = _windows_open_file(path, 0x80000000 | 0x00010000, 0x00000001)
        anchor_handle = _windows_open_file(
            anchor,
            0x80000000,
            0x00000001 | 0x00000002 | 0x00000004,
        )
        if _windows_file_identity(temporary_handle) != _windows_file_identity(anchor_handle):
            raise ConflictError(f"restore binding temporary physical identity changed: {path}")
        if _windows_read_handle(temporary_handle) != expected:
            raise ConflictError(f"restore binding temporary ownership changed: {path}")
        _after_restore_owned_temporary_compared(path)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        set_information = kernel32.SetFileInformationByHandle
        set_information.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        set_information.restype = ctypes.c_int

        class FileDispositionInfo(ctypes.Structure):
            _fields_ = [("delete_file", ctypes.c_ubyte)]

        disposition = FileDispositionInfo(1)
        if not set_information(
            temporary_handle,
            4,
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    except ConflictError:
        raise
    except OSError as exc:
        raise ArsError(f"restore binding could not seal temporary cleanup: {path}") from exc
    finally:
        close_error: OSError | None = None
        for handle in (anchor_handle, temporary_handle):
            if handle != -1:
                try:
                    _windows_close_handle(handle)
                except OSError as exc:
                    close_error = exc
        if close_error is not None:
            raise ArsError(f"restore binding could not close sealed cleanup handle: {path}") from close_error


def _posix_file_identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _posix_open_regular(path: Path, *, label: str) -> int:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ConflictError(f"restore binding {label} is not a regular file: {path}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _posix_file_identity(opened) != _posix_file_identity(metadata):
            raise ConflictError(f"restore binding {label} physical identity changed: {path}")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _posix_read_descriptor(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _posix_compare_owned_temporary(path: Path, anchor: Path, expected: bytes) -> None:
    temporary_descriptor = -1
    anchor_descriptor = -1
    try:
        temporary_descriptor = _posix_open_regular(path, label="temporary")
        anchor_descriptor = _posix_open_regular(anchor, label="anchor")
        temporary_identity = _posix_file_identity(os.fstat(temporary_descriptor))
        anchor_identity = _posix_file_identity(os.fstat(anchor_descriptor))
        if temporary_identity != anchor_identity:
            raise ConflictError(f"restore binding temporary physical identity changed: {path}")
        if _posix_read_descriptor(temporary_descriptor) != expected:
            raise ConflictError(f"restore binding temporary ownership changed: {path}")
    except ConflictError:
        raise
    except OSError as exc:
        raise ArsError(f"restore binding could not seal temporary cleanup: {path}") from exc
    finally:
        close_error: OSError | None = None
        for descriptor in (anchor_descriptor, temporary_descriptor):
            if descriptor != -1:
                try:
                    os.close(descriptor)
                except OSError as exc:
                    close_error = exc
        if close_error is not None:
            raise ArsError(f"restore binding could not close sealed cleanup descriptor: {path}") from close_error


def _posix_cleanup_quarantine(path: Path) -> tuple[Path, Path]:
    for _ in range(8):
        directory = path.parent / f".{path.name}.restore-cleanup-quarantine-{secrets.token_hex(16)}"
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            continue
        except OSError as exc:
            raise ArsError(f"restore binding could not reserve cleanup quarantine: {path}") from exc
        return directory, directory / path.name
    raise ConflictError(f"restore binding cleanup quarantine name conflicts: {path}")


def _posix_restore_quarantined_path(quarantined: Path, path: Path) -> None:
    try:
        os.link(quarantined, path, follow_symlinks=False)
    except FileExistsError as exc:
        raise ConflictError(
            f"restore binding temporary replacement remains quarantined without overwriting current path: {quarantined}"
        ) from exc
    except OSError as exc:
        raise ArsError(f"restore binding temporary replacement remains quarantined: {quarantined}") from exc


def _posix_delete_owned_temporary(path: Path, anchor: Path, expected: bytes) -> None:
    _posix_compare_owned_temporary(path, anchor, expected)
    _after_restore_owned_temporary_compared(path)
    _posix_compare_owned_temporary(path, anchor, expected)
    quarantine_directory, quarantined = _posix_cleanup_quarantine(path)
    try:
        os.rename(path, quarantined)
    except OSError as exc:
        try:
            os.rmdir(quarantine_directory)
        except OSError:
            pass
        raise ArsError(f"restore binding could not quarantine temporary cleanup: {path}") from exc
    try:
        _posix_compare_owned_temporary(quarantined, anchor, expected)
    except ArsError:
        _posix_restore_quarantined_path(quarantined, path)
        raise
    # POSIX pathname unlink cannot bind deletion to the verified inode. Retain
    # the private quarantine artifact for separately governed cleanup/evidence.


def _cleanup_owned_temporary(path: Path, expected: bytes, *, anchor: Path) -> None:
    if os.name == "nt":
        if not path.exists():
            if not _fsync_directory(path.parent):
                raise ArsError("restore binding requires durable temporary cleanup")
            return
        _before_restore_owned_temporary_cleanup(path)
        _windows_delete_owned_temporary(path, anchor, expected)
        if path.exists():
            raise ConflictError(f"restore binding temporary name was replaced during cleanup: {path}")
    else:
        try:
            path.lstat()
        except FileNotFoundError:
            if not _fsync_directory(path.parent):
                raise ArsError("restore binding requires durable temporary cleanup")
            return
        _before_restore_owned_temporary_cleanup(path)
        _posix_delete_owned_temporary(path, anchor, expected)
        try:
            path.lstat()
        except FileNotFoundError:
            pass
        else:
            raise ConflictError(f"restore binding temporary name was replaced during cleanup: {path}")
    if not _fsync_directory(path.parent):
        raise ArsError("restore binding requires durable temporary cleanup")


def _cleanup_current_transaction_temporary(target: Path, record: dict[str, Any], record_raw: bytes) -> None:
    temporary = _transaction_transition_path(
        target,
        str(record["transaction_id"]),
        int(record["generation"]),
    )
    _cleanup_owned_temporary(
        temporary,
        record_raw,
        anchor=restore_binding_transaction_path(target),
    )


def _write_initial_transaction(target: Path, value: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    path = restore_binding_transaction_path(target)
    data = canonical_bytes(value)
    temporary = _transaction_transition_path(target, str(value["transaction_id"]), 0)
    existing = _file_bytes(temporary)
    if existing is None:
        _write_exclusive(temporary, data)
    elif existing != data:
        raise ConflictError("restore binding prepared-record temporary conflicts")
    if not _fsync_directory(temporary.parent):
        raise ArsError("restore binding requires durable prepared-record temporary")
    _after_restore_initial_transaction_temporary_durable(temporary)
    try:
        os.link(temporary, path)
    except FileExistsError as exc:
        raise ConflictError("restore binding transaction already exists") from exc
    if not _fsync_directory(path.parent):
        raise ArsError("restore binding requires durable prepared transaction")
    _cleanup_owned_temporary(temporary, data, anchor=path)
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
        if not path.parent.exists():
            _require_physical_restore_path(target, path.parent.parent)
            path.parent.mkdir()
            _require_physical_restore_path(target, path.parent)
            if not _fsync_directory(path.parent) or not _fsync_directory(path.parent.parent):
                raise ArsError("restore binding requires durable physical output directory")
        _write_exclusive(path, data)
        if not _fsync_directory(path.parent):
            raise ArsError("restore binding requires durable temporary preparation")
    elif existing != data:
        raise ConflictError(f"restore binding temporary ownership conflict: {path}")
    return path, data


def _publish_restore_approval(target: Path, approval: dict[str, Any]) -> tuple[str, str]:
    data = canonical_bytes(approval)
    digest = sha256_hex(data)
    path = restore_binding_approval_object_path(target, digest)
    directory = path.parent
    if not directory.exists():
        _require_physical_restore_path(target, directory.parent)
        directory.mkdir()
        _require_physical_restore_path(target, directory)
        if not _fsync_directory(directory) or not _fsync_directory(directory.parent):
            raise ArsError("restore binding requires durable physical approval directory")
    _require_physical_restore_path(target, path)
    if not _fsync_directory(directory) or not _fsync_directory(directory.parent):
        raise ArsError("restore binding approval directory lacks durability confirmation")
    candidates = set(directory.glob(f"{_RESTORE_APPROVAL_PREFIX}*.json"))
    if candidates and candidates != {path}:
        raise ConflictError("restore approval exact-set closure conflicts")
    temporary = directory / f".{path.name}.{digest}.tmp"
    temporary_candidates = set(directory.glob(f".{_RESTORE_APPROVAL_PREFIX}*.tmp"))
    if temporary_candidates and temporary_candidates != {temporary}:
        raise ConflictError("restore approval temporary exact-set closure conflicts")
    existing = _file_bytes(path)
    if existing is not None:
        if existing != data:
            raise ConflictError("restore approval content-addressed object conflicts")
        if not _fsync_directory(directory):
            raise ArsError("restore binding requires durable approval confirmation")
        _cleanup_owned_temporary(temporary, data, anchor=path)
        return digest, _relative_path(target, path)
    temporary_bytes = _file_bytes(temporary)
    if temporary_bytes is None:
        _write_exclusive(temporary, data)
        if not _fsync_directory(directory):
            raise ArsError("restore binding requires durable approval preparation")
    elif temporary_bytes != data:
        raise ConflictError("restore approval temporary ownership conflicts")
    elif not _fsync_directory(directory):
        raise ArsError("restore binding approval temporary lacks durability confirmation")
    try:
        os.link(temporary, path)
    except FileExistsError:
        if _file_bytes(path) != data:
            raise ConflictError("restore approval content-addressed object conflicts")
    if _file_bytes(path) != data or not _fsync_directory(directory):
        raise ArsError("restore binding requires durable approval publication")
    _cleanup_owned_temporary(temporary, data, anchor=path)
    return digest, _relative_path(target, path)


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
        if not _fsync_directory(output.parent):
            raise ArsError("restore binding requires durable output confirmation")
        _cleanup_owned_temporary(temporary, temporary_bytes, anchor=output)
        return
    temporary, temporary_bytes = _prepare_owned_temporary(target, record, "output")
    _require_physical_restore_path(target, output.parent)
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
    _cleanup_owned_temporary(temporary, temporary_bytes, anchor=output)


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
        if not _fsync_directory(path.parent):
            raise ArsError("restore binding requires durable canonical confirmation")
        _cleanup_owned_temporary(temporary, temporary_bytes, anchor=path)
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
    _cleanup_owned_temporary(temporary, temporary_bytes, anchor=path)


def _build_restore_evidence(
    *,
    transaction_id: str,
    approval_relative: str,
    approval_sha256: str,
    restore_preflight_result_hash: str,
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
    origin_witness_path: str,
    origin_witness_sha256: str,
    origin_initial_control_root: str,
    origin_initial_physical_root_identity: dict[str, str],
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
        "approval_object_path": approval_relative,
        "approval_sha256": approval_sha256,
        "restore_preflight_result_hash": restore_preflight_result_hash,
        "output_object_path": output_relative,
        "output_object_sha256": output_digest,
        "actor_id": actor_id,
        "authority_grant_id": authority_grant_id,
        "code_roots": code_roots,
        "schema_root": schema_root,
        "source_root_identity": dict(origin_initial_physical_root_identity),
        "origin_witness_path": origin_witness_path,
        "origin_witness_sha256": origin_witness_sha256,
        "origin_initial_control_root": origin_initial_control_root,
        "origin_initial_physical_root_identity": dict(origin_initial_physical_root_identity),
    }


def _build_restore_transaction(
    *,
    transaction_id: str,
    approval_relative: str,
    approval_sha256: str,
    restore_preflight_result_hash: str,
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
    origin_witness_path: str,
    origin_witness_sha256: str,
    origin_initial_control_root: str,
    origin_initial_physical_root_identity: dict[str, str],
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
        "approval_object_path": approval_relative,
        "approval_sha256": approval_sha256,
        "restore_preflight_result_hash": restore_preflight_result_hash,
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
        "origin_witness_path": origin_witness_path,
        "origin_witness_sha256": origin_witness_sha256,
        "origin_initial_control_root": origin_initial_control_root,
        "origin_initial_physical_root_identity": dict(origin_initial_physical_root_identity),
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
    approval_sha256: str,
    restore_preflight_result_hash: str,
    origin_witness_path: str,
    origin_witness_sha256: str,
    origin_initial_control_root: str,
    origin_initial_physical_root_identity: dict[str, str],
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
        "approval_sha256": approval_sha256,
        "restore_preflight_result_hash": restore_preflight_result_hash,
        "origin_witness_path": origin_witness_path,
        "origin_witness_sha256": origin_witness_sha256,
        "origin_initial_control_root": origin_initial_control_root,
        "origin_initial_physical_root_identity": origin_initial_physical_root_identity,
    }
    for field, value in expected.items():
        if record[field] != value:
            raise ConflictError(f"restore binding transaction input changed: {field}")
    _require_root_identity(source, record["source_root_identity"])
    _require_root_identity(target, record["target_root_identity"])


def _validate_restore_join(
    target: Path,
    record: dict[str, Any],
    *,
    approved_witness_path: Path | None = None,
) -> dict[str, Any]:
    approval, _ = _read_restore_approval(target, str(record["approval_sha256"]))
    preflight = approval["restore_preflight"]
    if approved_witness_path is not None:
        expected_witness_path = str(approved_witness_path)
        for field, value in {
            "record": record.get("origin_witness_path"),
            "preflight": preflight.get("origin_witness_path"),
            "approval": approval.get("origin_witness_path"),
        }.items():
            if value != expected_witness_path:
                raise IntegrityError(f"restore {field} origin witness path differs from foundation")
    approval_path = restore_binding_approval_object_path(target, str(record["approval_sha256"]))
    approval_relative = _relative_path(target, approval_path)
    source = Path(str(preflight["source_root"])).resolve(strict=False)
    intended_unsigned = approval["rebound_manifest"]
    intended_manifest_value = dict(intended_unsigned)
    intended_manifest_value["manifest_hash"] = _restored_manifest_hash(
        intended_manifest_value,
        str(record["approval_sha256"]),
    )
    independently_intended_manifest = canonical_bytes(intended_manifest_value)
    independently_expected_output = canonical_restore_binding_output(
        target,
        str(preflight["project_id"]),
        str(preflight["store_identity"]),
        [Path(root) for root in preflight["code_roots"]],
        Path(str(preflight["schema_root"])),
    )
    output_digest = sha256_hex(independently_expected_output)
    output_relative = _relative_path(target, restore_binding_output_object_path(target, output_digest))
    independently_expected_evidence = canonical_bytes(
        _build_restore_evidence(
            transaction_id=str(record["approval_sha256"]),
            approval_relative=approval_relative,
            approval_sha256=str(record["approval_sha256"]),
            restore_preflight_result_hash=str(preflight["result_hash"]),
            source=source,
            target=target,
            project_id=str(preflight["project_id"]),
            store_identity=str(preflight["store_identity"]),
            manifest=intended_manifest_value,
            manifest_bytes=independently_intended_manifest,
            receipt_hash=str(preflight["receipt_hash"]),
            source_snapshot=approval["source_snapshot"],
            source_snapshot_hash=str(preflight["source_snapshot_hash"]),
            output_bytes=independently_expected_output,
            output_relative=output_relative,
            actor_id=str(preflight["actor_id"]),
            authority_grant_id=str(preflight["authority_grant_id"]),
            code_roots=list(preflight["code_roots"]),
            schema_root=str(preflight["schema_root"]),
            origin_witness_path=str(preflight["origin_witness_path"]),
            origin_witness_sha256=str(preflight["origin_witness_sha256"]),
            origin_initial_control_root=str(preflight["origin_initial_control_root"]),
            origin_initial_physical_root_identity=dict(preflight["origin_initial_physical_root_identity"]),
        )
    )
    anchored_fields = {
        "transaction_id": record["approval_sha256"],
        "approval_object_path": approval_relative,
        "restore_preflight_result_hash": preflight["result_hash"],
        "source_root": preflight["source_root"],
        "target_root": preflight["target_root"],
        "source_root_identity": approval["source_root_identity"],
        "target_root_identity": approval["target_root_identity"],
        "project_id": preflight["project_id"],
        "store_identity": preflight["store_identity"],
        "receipt_hash": preflight["receipt_hash"],
        "actor_id": preflight["actor_id"],
        "authority_grant_id": preflight["authority_grant_id"],
        "source_snapshot": approval["source_snapshot"],
        "source_snapshot_hash": preflight["source_snapshot_hash"],
        "code_roots": preflight["code_roots"],
        "schema_root": preflight["schema_root"],
        "origin_witness_path": preflight["origin_witness_path"],
        "origin_witness_sha256": preflight["origin_witness_sha256"],
        "origin_initial_control_root": preflight["origin_initial_control_root"],
        "origin_initial_physical_root_identity": preflight["origin_initial_physical_root_identity"],
        "target_pre_state_sha256": approval["original_manifest_sha256"],
        "original_manifest_sha256": approval["original_manifest_sha256"],
        "intended_manifest_bytes": independently_intended_manifest.hex(),
        "intended_manifest_sha256": sha256_hex(independently_intended_manifest),
        "intended_evidence_bytes": independently_expected_evidence.hex(),
        "intended_evidence_sha256": sha256_hex(independently_expected_evidence),
        "output_object_path": output_relative,
        "output_object_sha256": output_digest,
        "output_object_bytes": independently_expected_output.hex(),
    }
    for field, expected in anchored_fields.items():
        if record[field] != expected:
            raise IntegrityError(f"restore binding transaction differs from immutable approval: {field}")
    if (
        sha256_hex(_from_hex(record["original_manifest_bytes"], "original_manifest_bytes") or b"")
        != approval["original_manifest_sha256"]
    ):
        raise IntegrityError("restore binding original manifest differs from immutable approval")
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
    manifest = _read_manifest(
        manifest_path,
        require_canonical=True,
        restore_approval_sha256=str(record["approval_sha256"]),
    )
    if (
        manifest.get("origin_witness_sha256") != record["origin_witness_sha256"]
        or manifest.get("origin_witness_path") != record["origin_witness_path"]
        or manifest.get("origin_initial_control_root") != record["origin_initial_control_root"]
    ):
        raise IntegrityError("restore binding manifest origin witness join is invalid")
    evidence, evidence_raw = _read_restore_binding_evidence(target)
    if evidence is None or evidence_raw != intended_evidence:
        raise IntegrityError("restore binding evidence join is missing")
    if (
        evidence["transaction_id"] != record["transaction_id"]
        or evidence["approval_object_path"] != approval_relative
        or evidence["approval_sha256"] != record["approval_sha256"]
        or evidence["restore_preflight_result_hash"] != preflight["result_hash"]
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
        or evidence["origin_witness_path"] != record["origin_witness_path"]
        or evidence["origin_witness_sha256"] != record["origin_witness_sha256"]
        or evidence["origin_initial_control_root"] != record["origin_initial_control_root"]
        or evidence["source_root_identity"] != record["origin_initial_physical_root_identity"]
    ):
        raise IntegrityError("restore binding transaction/evidence/manifest/output join is invalid")
    if approved_witness_path is not None and evidence["origin_witness_path"] != str(approved_witness_path):
        raise IntegrityError("restore evidence origin witness path differs from foundation")
    return manifest


def _require_cleared_without_temporaries(target: Path, record: dict[str, Any]) -> None:
    transition_temporaries = any((target / "manifests").glob(".restore-binding-transaction.*.tmp"))
    approval_temporaries = any(
        (target / "manifests" / _RESTORE_BINDING_OUTPUT_DIRECTORY).glob(f".{_RESTORE_APPROVAL_PREFIX}*.tmp")
    )
    if (
        transition_temporaries
        or approval_temporaries
        or any(_record_path(target, str(item["relative_path"])).exists() for item in record["temporaries"].values())
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
    expected_restore_preflight: dict[str, Any] | None = None,
    approved_witness: StoreOriginWitness | None = None,
    approved_witness_path: Path | None = None,
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
        or expected_restore_preflight is None
        or approved_witness is None
    ):
        raise ArsError("complete approved restore transaction inputs are required")
    if not isinstance(approved_witness, StoreOriginWitness):
        raise ArsError("approved origin witness is required")
    resolved_witness_path, origin_root = _validate_approved_origin_witness_path(
        approved_witness_path,
        approved_witness,
    )
    witness_path_value = str(resolved_witness_path)
    if sha256_hex(approved_witness.raw_bytes) != approved_witness.raw_sha256:
        raise IntegrityError("approved origin witness bytes are invalid")
    code_paths = [root.resolve(strict=True) for root in expected_code_roots]
    target = require_existing_control_root(code_paths, target_root)
    source = require_existing_control_root(code_paths, source_root)
    if source == target:
        raise ConflictError("restored store source must differ from target")
    _require_physical_disjoint(
        origin_root,
        source,
        message="origin authority root must be physically disjoint from the restore source",
    )
    _require_physical_disjoint(
        origin_root,
        target,
        message="origin authority root must be physically disjoint from the restored target",
    )
    schema = expected_schema_root.resolve(strict=True)
    code_values = sorted(str(root) for root in code_paths)
    source_manifest = load_store_manifest(
        source,
        approved_witness=approved_witness,
        approved_witness_path=resolved_witness_path,
    )
    if sha256_hex(canonical_bytes(source_manifest)) != approved_witness.initial_manifest_sha256:
        raise IntegrityError("restore source manifest differs from approved origin witness")
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
    preflight = _validate_preflight_approval(expected_restore_preflight)
    preflight_expected = {
        "target_root": str(target),
        "source_root": str(source),
        "project_id": expected_project_id,
        "store_identity": expected_store_identity,
        "receipt_hash": expected_restore_receipt_hash,
        "actor_id": actor_id,
        "authority_grant_id": authority_grant_id,
        "source_snapshot_hash": expected_source_snapshot_hash,
        "code_roots": code_values,
        "schema_root": str(schema),
        "expected_output_sha256": sha256_hex(output_bytes),
        "origin_witness_path": witness_path_value,
        "origin_witness_sha256": approved_witness.raw_sha256,
        "origin_initial_control_root": approved_witness.initial_control_root,
        "origin_initial_physical_root_identity": approved_witness.initial_physical_root_identity,
    }
    for field, expected in preflight_expected.items():
        if preflight[field] != expected:
            raise ConflictError(f"restore preflight approval changed: {field}")

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
        if preflight["target_manifest_bytes_sha256"] != sha256_hex(original_manifest):
            raise ConflictError("restore preflight target manifest changed before restore binding")
        if manifest.get("project_id") != expected_project_id:
            raise ConflictError("project identity mismatch")
        if manifest.get("store_identity") != expected_store_identity:
            raise ConflictError("store identity mismatch")
        if sha256_hex(original_manifest) != approved_witness.initial_manifest_sha256:
            raise ConflictError("restore target manifest differs from approved origin witness")
        if manifest.get("control_root") != approved_witness.initial_control_root:
            raise ConflictError("restore target source lineage differs from approved origin witness")
        if manifest.get("code_roots") != code_values:
            raise ConflictError("code root binding mismatch")
        persisted_schema = manifest_schema_root(manifest)
        if persisted_schema is None or persisted_schema.resolve(strict=False) != schema:
            raise ConflictError("schema root binding mismatch")
        rebound = dict(manifest)
        rebound["control_root"] = str(target)
        rebound["origin_witness_path"] = witness_path_value
        rebound["origin_witness_sha256"] = approved_witness.raw_sha256
        rebound["origin_initial_control_root"] = approved_witness.initial_control_root
        rebound["origin_initial_physical_root_identity"] = dict(approved_witness.initial_physical_root_identity)
        rebound.pop("manifest_hash", None)
        approval = _build_restore_approval(
            restore_preflight=preflight,
            source=source,
            target=target,
            source_snapshot=source_snapshot,
            original_manifest=original_manifest,
            rebound_manifest=rebound,
        )
        approval_raw = canonical_bytes(approval)
        approval_sha256 = sha256_hex(approval_raw)
        _validate_restore_approval(target, approval, approval_raw)
        initial_temporary = _transaction_transition_path(target, approval_sha256, 0)
        initial_candidates = set((target / "manifests").glob(".restore-binding-transaction.*.tmp"))
        if initial_candidates and initial_candidates != {initial_temporary}:
            raise ConflictError("restore binding initial temporary exact-set closure conflicts")
        published_approval_sha256, approval_relative = _publish_restore_approval(target, approval)
        if published_approval_sha256 != approval_sha256:
            raise IntegrityError("restore approval publication digest changed")
        rebound["manifest_hash"] = _restored_manifest_hash(rebound, approval_sha256)
        intended_manifest = canonical_bytes(rebound)
        transaction_id = approval_sha256
        output_digest = sha256_hex(output_bytes)
        output_relative = _relative_path(target, restore_binding_output_object_path(target, output_digest))
        evidence = _build_restore_evidence(
            transaction_id=transaction_id,
            approval_relative=approval_relative,
            approval_sha256=approval_sha256,
            restore_preflight_result_hash=str(preflight["result_hash"]),
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
            origin_witness_path=witness_path_value,
            origin_witness_sha256=approved_witness.raw_sha256,
            origin_initial_control_root=approved_witness.initial_control_root,
            origin_initial_physical_root_identity=dict(approved_witness.initial_physical_root_identity),
        )
        intended_evidence = canonical_bytes(evidence)
        record = _build_restore_transaction(
            transaction_id=transaction_id,
            approval_relative=approval_relative,
            approval_sha256=approval_sha256,
            restore_preflight_result_hash=str(preflight["result_hash"]),
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
            origin_witness_path=witness_path_value,
            origin_witness_sha256=approved_witness.raw_sha256,
            origin_initial_control_root=approved_witness.initial_control_root,
            origin_initial_physical_root_identity=dict(approved_witness.initial_physical_root_identity),
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
        approval, _ = _read_restore_approval(target, str(record["approval_sha256"]))
        if approval["restore_preflight"] != preflight:
            raise ConflictError("restore preflight differs from immutable approval")
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
            approval_sha256=sha256_hex(canonical_bytes(approval)),
            restore_preflight_result_hash=str(preflight["result_hash"]),
            origin_witness_path=witness_path_value,
            origin_witness_sha256=approved_witness.raw_sha256,
            origin_initial_control_root=approved_witness.initial_control_root,
            origin_initial_physical_root_identity=dict(approved_witness.initial_physical_root_identity),
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
            _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
            if finalization_validator is not None:
                finalization_validator()
            validate_physical_roots(record)
            return _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
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
        _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
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
        _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
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
        _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
        record, record_raw = _transition_transaction(
            target,
            record,
            record_raw,
            state="committed",
            durability_step="commit-durable",
        )

    if record["state"] == "committed":
        validate_physical_roots(record)
        _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
        record, record_raw = _transition_transaction(
            target,
            record,
            record_raw,
            state="cleared",
            durability_step="clear-durable",
        )
        validate_physical_roots(record)
        _require_cleared_without_temporaries(target, record)
        return _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
    raise IntegrityError(f"unsupported restore binding transaction state: {record['state']}")


def verify_restore_binding_admission(
    control_root: Path,
    *,
    approved_witness: StoreOriginWitness | None = None,
    approved_witness_path: Path | None = None,
) -> dict[str, Any] | None:
    """Read-only admission for never-restored or durably cleared stores."""
    if not isinstance(approved_witness, StoreOriginWitness):
        raise IntegrityError("approved origin witness is required")
    target = control_root.resolve(strict=True)
    _assert_no_second_restore_authority(target)
    record, _ = _read_restore_binding_transaction(target)
    resolved_witness_path: Path | None = None
    origin_root: Path | None = None
    if record is not None or approved_witness_path is not None:
        resolved_witness_path, origin_root = _validate_approved_origin_witness_path(
            approved_witness_path,
            approved_witness,
        )
        _require_physical_disjoint(
            origin_root,
            target,
            message="origin authority root must be physically disjoint from the restored target",
        )
    evidence_raw = _file_bytes(_restore_binding_evidence_path(target))
    output_directory = target / "manifests" / _RESTORE_BINDING_OUTPUT_DIRECTORY
    restore_directory_exists = output_directory.exists()
    if restore_directory_exists:
        _require_physical_restore_path(target, output_directory)
    outputs_exist = restore_directory_exists and any(output_directory.glob("sha256-*.json"))
    approvals_exist = restore_directory_exists and any(output_directory.glob(f"{_RESTORE_APPROVAL_PREFIX}*.json"))
    transition_temporaries = any((target / "manifests").glob(".restore-binding-transaction.*.tmp"))
    if record is None:
        manifest = _read_manifest(_manifest_path(target), require_canonical=False)
        _validate_manifest_identity(manifest)
        _validate_external_witness_for_store(target, manifest, approved_witness)
        if (
            evidence_raw is not None
            or restore_directory_exists
            or outputs_exist
            or approvals_exist
            or transition_temporaries
        ):
            raise IntegrityError("partial restore binding exists without a transaction record")
        return None
    if record["state"] != "cleared":
        raise IntegrityError(f"restore binding transaction state is not cleared: {record['state']}")
    if (
        record.get("origin_witness_sha256") != approved_witness.raw_sha256
        or record.get("origin_witness_path") is None
        or record.get("origin_initial_control_root") != approved_witness.initial_control_root
        or record.get("origin_initial_physical_root_identity") != approved_witness.initial_physical_root_identity
    ):
        raise IntegrityError("cleared restore binding origin witness differs from approved witness")
    if record.get("source_root") != approved_witness.initial_control_root:
        raise IntegrityError("cleared restore binding source lineage differs from approved witness")
    if record.get("source_root_identity") != approved_witness.initial_physical_root_identity:
        raise IntegrityError("cleared restore binding source identity differs from approved witness")
    source = Path(str(record["source_root"]))
    if origin_root is None or resolved_witness_path is None:
        raise IntegrityError("foundation-approved origin witness path is required")
    _require_physical_disjoint(
        origin_root,
        source,
        message="origin authority root must be physically disjoint from the restore source",
    )
    _require_cleared_without_temporaries(target, record)
    _require_root_identity(target, record["target_root_identity"])
    _validate_restore_join(target, record, approved_witness_path=resolved_witness_path)
    return record


def verify_store_identity(
    control_root: Path,
    expected_project_id: str,
    expected_store_identity: str,
    expected_code_roots: list[Path] | None = None,
    *,
    approved_witness: StoreOriginWitness | None = None,
    approved_witness_path: Path | None = None,
) -> str:
    manifest = load_store_manifest(
        control_root,
        approved_witness=approved_witness,
        approved_witness_path=approved_witness_path,
    )
    if manifest["project_id"] != expected_project_id:
        raise ArsError("store project identity mismatch")
    if manifest["store_identity"] != expected_store_identity:
        raise ArsError("store identity mismatch")
    if expected_code_roots is not None:
        resolved = sorted(str(root.resolve(strict=True)) for root in expected_code_roots)
        if manifest.get("code_roots") != resolved:
            raise ArsError("code root binding mismatch")
    return str(manifest["store_identity"])
