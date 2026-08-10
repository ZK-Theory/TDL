from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.ids import validate_id
from research_system.store.identity import (
    load_restore_binding_transaction,
    load_store_manifest_unbound,
    manifest_schema_root,
)
from research_system.store.objects import ObjectStore


_ACTIVATION_DIRECTORY = "schema-bindings"
_ACTIVATION_POINTER = "schema-binding-activation.json"
_REQUIRED_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "project_id",
        "store_identity",
        "control_root",
        "code_roots",
        "prior_schema_root",
        "schema_root",
        "owner_decision_id",
        "contract_sha256",
        "contract_schema_sha256",
        "pack_schema_sha256",
        "activated_at",
    }
)


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise IntegrityError(f"schema binding activation {field} is invalid")
    try:
        int(value, 16)
    except ValueError as exc:
        raise IntegrityError(f"schema binding activation {field} is invalid") from exc
    return value


def _activation_pointer(control_root: Path) -> Path:
    return control_root / "manifests" / _ACTIVATION_POINTER


def schema_binding_activation_object_path(control_root: Path, digest: str) -> Path:
    """Return the content-addressed path for one schema-binding activation.

    Args:
        control_root: Canonical Control-store root containing the manifests directory.
        digest: Lowercase SHA-256 digest of the canonical activation bytes.

    Returns:
        The expected immutable activation-object path.

    Raises:
        IntegrityError: If ``digest`` is not a lowercase SHA-256 value.
    """
    return control_root / "manifests" / _ACTIVATION_DIRECTORY / f"sha256-{_digest(digest, 'digest')}.json"


def _validate_owner_decision(value: Mapping[str, Any], *, control_root: Path) -> None:
    owner_decision_id = str(value["owner_decision_id"])
    try:
        decision = ObjectStore(control_root).read(
            "stephen_contract_schema_acceptance",
            owner_decision_id,
            1,
        )
    except (IntegrityError, ValueError) as exc:
        raise IntegrityError("schema binding activation owner decision is unavailable") from exc
    if not isinstance(decision, Mapping):
        raise IntegrityError("schema binding activation owner decision is invalid")
    contract_subject = decision.get("contract_subject")
    pack_schema_subject = decision.get("pack_schema_subject")
    if not isinstance(contract_subject, Mapping) or not isinstance(pack_schema_subject, Mapping):
        raise IntegrityError("schema binding activation owner decision is invalid")
    if (
        decision.get("record_type") != "stephen_contract_schema_acceptance"
        or decision.get("owner_decision_id") != owner_decision_id
        or decision.get("outcome") != "accepted"
        or decision.get("decision_state") != "active"
        or contract_subject.get("canonical_sha256") != value["contract_sha256"]
        or pack_schema_subject.get("canonical_sha256") != value["pack_schema_sha256"]
    ):
        raise IntegrityError("schema binding activation owner decision does not authorize the exact artifacts")


def _validate_activation(value: dict[str, Any], *, control_root: Path) -> Path:
    if set(value) != _REQUIRED_FIELDS:
        raise IntegrityError("schema binding activation fields are invalid")
    if value["schema_id"] != "ars://internal/store-schema-binding-activation" or value["schema_version"] != "1.0.0":
        raise IntegrityError("schema binding activation identity is invalid")
    project_id = validate_id(str(value["project_id"]), "project")
    if project_id != value["project_id"]:
        raise IntegrityError("schema binding activation project is invalid")
    validate_id(str(value["owner_decision_id"]), "stephen_contract_schema_acceptance")
    _digest(value["store_identity"], "store_identity")
    for field in ("contract_sha256", "contract_schema_sha256", "pack_schema_sha256"):
        _digest(value[field], field)
    if value["control_root"] != str(control_root):
        raise IntegrityError("schema binding activation control root is invalid")
    roots = value["code_roots"]
    if not isinstance(roots, list) or not roots or any(not isinstance(root, str) for root in roots):
        raise IntegrityError("schema binding activation code roots are invalid")
    resolved_roots = [Path(root).resolve(strict=False) for root in roots]
    if roots != [str(root) for root in sorted(resolved_roots, key=str)] or len(set(resolved_roots)) != len(roots):
        raise IntegrityError("schema binding activation code roots are not canonical")
    for field in ("prior_schema_root", "schema_root"):
        if not isinstance(value[field], str) or not Path(value[field]).is_absolute():
            raise IntegrityError(f"schema binding activation {field} is invalid")
    schema_root = Path(value["schema_root"]).resolve(strict=True)
    if schema_root not in {root / ".research-system" / "schemas" for root in resolved_roots}:
        raise IntegrityError("schema binding activation schema root is not registered")
    if not isinstance(value["activated_at"], str) or not value["activated_at"].endswith("Z"):
        raise IntegrityError("schema binding activation time is invalid")
    manifest = load_store_manifest_unbound(control_root)
    restore = load_restore_binding_transaction(control_root)
    if restore is not None and restore.get("state") != "cleared":
        raise IntegrityError("schema binding activation requires a cleared restore transaction")
    prior = manifest_schema_root(manifest)
    if (
        manifest.get("project_id") != value["project_id"]
        or manifest.get("store_identity") != value["store_identity"]
        or manifest.get("code_roots") != roots
        or prior is None
        or str(prior.resolve(strict=True)) != value["prior_schema_root"]
    ):
        raise IntegrityError("schema binding activation differs from immutable store identity")
    expected_files = {
        "contract_sha256": schema_root.parent / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml",
        "contract_schema_sha256": schema_root / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json",
        "pack_schema_sha256": schema_root / "assurance" / "assurance-pack.schema.json",
    }
    for field, path in expected_files.items():
        try:
            actual = sha256_hex(path.read_bytes())
        except OSError as exc:
            raise IntegrityError(f"schema binding activation file is unavailable: {path}") from exc
        if actual != value[field]:
            raise IntegrityError(f"schema binding activation {field} differs from exact bytes")
    _validate_owner_decision(value, control_root=control_root)
    return schema_root


def load_store_schema_binding_activation(
    control_root: Path,
    *,
    expected_sha256: str,
) -> tuple[dict[str, Any], Path]:
    """Load and verify one immutable schema-binding activation.

    Args:
        control_root: Canonical Control-store root.
        expected_sha256: SHA-256 digest pinned by the approved project binding.

    Returns:
        The validated activation object and its effective schema root.

    Raises:
        IntegrityError: If the pointer, object, owner decision, store binding, or artifact bytes are missing,
            malformed, mismatched, or unauthorized.
    """
    control = control_root.resolve(strict=True)
    digest = _digest(expected_sha256, "digest")
    pointer = _activation_pointer(control)
    object_path = schema_binding_activation_object_path(control, digest)
    try:
        pointer_raw = pointer.read_bytes()
        object_raw = object_path.read_bytes()
    except OSError as exc:
        raise IntegrityError("schema binding activation is not materialized") from exc
    try:
        decoded = json.loads(object_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("schema binding activation bytes are invalid") from exc
    if pointer_raw != object_raw or sha256_hex(object_raw) != digest or canonical_bytes(decoded) != object_raw:
        raise IntegrityError("schema binding activation bytes are invalid")
    value = decoded
    if not isinstance(value, dict):
        raise IntegrityError("schema binding activation must be an object")
    schema_root = _validate_activation(value, control_root=control)
    return value, schema_root


def verify_effective_store_schema_root(
    control_root: Path,
    manifest: dict[str, Any],
    requested_schema_root: Path,
    *,
    activation_sha256: str | None,
) -> Path:
    """Verify and return the schema root authorized for a Control store.

    Args:
        control_root: Canonical Control-store root.
        manifest: Verified immutable store-identity manifest.
        requested_schema_root: Schema root requested by the current binding.
        activation_sha256: Optional approved activation digest when the requested root differs from the manifest.

    Returns:
        The verified effective schema root.

    Raises:
        IntegrityError: If the manifest lacks a schema root or the requested root is not authorized by an exact,
            owner-backed activation.
    """
    requested = requested_schema_root.resolve(strict=True)
    persisted = manifest_schema_root(manifest)
    if persisted is None:
        raise IntegrityError("store manifest has no schema root")
    if persisted.resolve(strict=True) == requested:
        return requested
    if activation_sha256 is None:
        raise IntegrityError("binding schema root differs from store manifest")
    _activation, activated = load_store_schema_binding_activation(
        control_root,
        expected_sha256=activation_sha256,
    )
    if activated != requested:
        raise IntegrityError("binding schema root differs from store activation")
    return requested


def publish_store_schema_binding_activation(control_root: Path, value: dict[str, Any]) -> tuple[str, Path]:
    """Validate and atomically publish one schema-binding activation.

    Args:
        control_root: Canonical Control-store root.
        value: Complete activation object binding the store, schema roots, owner decision, and artifact digests.

    Returns:
        The activation SHA-256 digest and immutable object path.

    Raises:
        ConflictError: If an activation path or pointer already contains foreign content.
        IntegrityError: If the activation, owner decision, store binding, or referenced artifact bytes are invalid.
    """
    control = control_root.resolve(strict=True)
    _validate_activation(value, control_root=control)
    raw = canonical_bytes(value)
    digest = sha256_hex(raw)
    pointer = _activation_pointer(control)
    object_path = schema_binding_activation_object_path(control, digest)
    if pointer.exists():
        existing, _ = load_store_schema_binding_activation(control, expected_sha256=digest)
        if existing != value:
            raise ConflictError("schema binding activation pointer has foreign content")
        return digest, object_path
    object_path.parent.mkdir(exist_ok=True)
    for path in (object_path, pointer):
        if path.exists():
            if not path.is_file() or path.read_bytes() != raw:
                raise ConflictError(f"schema binding activation path has foreign content: {path}")
            continue
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError as exc:
            raise ConflictError(f"schema binding activation path is unavailable: {path}") from exc
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    load_store_schema_binding_activation(control, expected_sha256=digest)
    return digest, object_path
