"""Bind command-envelope deletion manifests to the accepted retention validator.

Closes review finding m-2: the `CommandService.deletion_manifest_authorizer`
slot must not accept a trivial "always verified" callable. This module
provides the real authorizer factory, built from `validate_deletion_manifest_for_event`,
and a schema-validated loader for the `EvidenceStoreRegistry` it needs.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from research_system.errors import ConfigurationError
from research_system.evals.retention import (
    DeletionVerificationManifest,
    EvidenceStoreRegistry,
    LocationInspection,
    validate_deletion_manifest_for_event,
    validate_retention_policy,
)
from research_system.schema_registry import SchemaRegistry

_MANIFEST_FIELDS = (
    "evidence_id",
    "evidence_hash",
    "retention_rule_id",
    "policy_revision",
    "registry_hash",
    "actor_id",
    "authority_grant_id",
    "checked_locations",
    "unregistered_replicas",
    "inaccessible_locations",
    "reparse_locations",
    "canonical_payload_present",
    "canonical_scan_hash",
    "authority_current",
    "verified_at",
    "status",
    "manifest_hash",
)


def reconstruct_deletion_manifest(
    payload: dict[str, Any],
) -> DeletionVerificationManifest:
    """Rebuild a `DeletionVerificationManifest` from a command payload dict.

    The payload is untrusted input carried on a `VerifyEvidenceDeletion`
    command envelope. Every field is read explicitly and any absence or
    malformed shape raises immediately rather than being defaulted or
    silently coerced -- reconstruction fails closed.

    Args:
        payload: The command's `payload` dict, expected to be the full
            JSON-round-tripped serialization of a
            `DeletionVerificationManifest` (as produced by
            `retention._jsonable(dataclasses.asdict(manifest))`).

    Returns:
        The reconstructed manifest. Its `manifest_hash` and other fields are
        not yet trusted -- callers must still pass it through
        `validate_deletion_manifest_for_event`.

    Raises:
        ValueError: If the payload is not an object, a required field is
            missing, or a field has the wrong shape.
    """
    if not isinstance(payload, dict):
        raise ValueError("deletion manifest payload must be an object")
    missing = [field for field in _MANIFEST_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"deletion manifest payload missing fields: {', '.join(missing)}")
    unexpected = sorted(set(payload) - set(_MANIFEST_FIELDS))
    if unexpected:
        raise ValueError(
            f"deletion manifest payload has unexpected fields: {', '.join(unexpected)}"
        )
    raw_checked = payload["checked_locations"]
    if not isinstance(raw_checked, list) or not all(
        isinstance(location, dict) for location in raw_checked
    ):
        raise ValueError("deletion manifest checked_locations must be a list of objects")
    for field in ("unregistered_replicas", "inaccessible_locations"):
        value = payload[field]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError(f"deletion manifest {field} must be a list of strings")
    raw_reparse = payload["reparse_locations"]
    if not isinstance(raw_reparse, list) or not all(
        isinstance(pair, (list, tuple))
        and len(pair) == 2
        and all(isinstance(item, str) for item in pair)
        for pair in raw_reparse
    ):
        raise ValueError(
            "deletion manifest reparse_locations must be a list of string pairs"
        )
    try:
        checked_locations = tuple(
            LocationInspection(
                resolved_path=location["resolved_path"],
                absent=location["absent"],
                evidence_hash=location["evidence_hash"],
                inspection_hash=location["inspection_hash"],
                inaccessible=location["inaccessible"],
                reparse_target=location["reparse_target"],
            )
            for location in raw_checked
        )
        reparse_locations = tuple(tuple(pair) for pair in raw_reparse)
        manifest = DeletionVerificationManifest(
            evidence_id=payload["evidence_id"],
            evidence_hash=payload["evidence_hash"],
            retention_rule_id=payload["retention_rule_id"],
            policy_revision=payload["policy_revision"],
            registry_hash=payload["registry_hash"],
            actor_id=payload["actor_id"],
            authority_grant_id=payload["authority_grant_id"],
            checked_locations=checked_locations,
            unregistered_replicas=tuple(payload["unregistered_replicas"]),
            inaccessible_locations=tuple(payload["inaccessible_locations"]),
            reparse_locations=reparse_locations,
            canonical_payload_present=payload["canonical_payload_present"],
            canonical_scan_hash=payload["canonical_scan_hash"],
            authority_current=payload["authority_current"],
            verified_at=payload["verified_at"],
            status=payload["status"],
            manifest_hash=payload["manifest_hash"],
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"malformed deletion manifest payload: {exc}") from exc
    return manifest


def build_deletion_manifest_authorizer(
    registry: EvidenceStoreRegistry,
    *,
    retention_policy_path: Path,
) -> Callable[[dict[str, Any], str, str], dict[str, Any]]:
    """Build a `CommandService.deletion_manifest_authorizer` closure.

    The returned closure holds no out-of-band manifest: it reconstructs a
    `DeletionVerificationManifest` from exactly what the command envelope
    carries and validates it against the accepted evidence-store registry.
    `actor_id` and `authority_grant_id` are taken from the command envelope
    arguments, never re-read from the payload, so a payload whose embedded
    actor/grant diverges from the submitting envelope is rejected by
    `validate_deletion_manifest_for_event`'s authority check, and a tampered
    field is rejected by its manifest-hash re-derivation.

    The current policy revision is independently loaded and validated from the
    canonical tracked policy path at construction time; it is never trusted from
    the evidence-store registry or command payload.

    Args:
        registry: The trusted, schema-validated evidence-store registry.
        retention_policy_path: Canonical `retention-policy.yaml` path used to
            validate and extract the currently accepted policy revision.

    Returns:
        A callable matching `CommandService.deletion_manifest_authorizer`:
        `(payload, actor_id, authority_grant_id) -> dict`.
    """
    policy = validate_retention_policy(Path(retention_policy_path))
    current_policy_revision = policy.get("policy_revision")
    if not isinstance(current_policy_revision, str):
        raise ConfigurationError("retention policy revision must be a string")

    def authorize(
        payload: dict[str, Any],
        actor_id: str,
        authority_grant_id: str,
    ) -> dict[str, Any]:
        manifest = reconstruct_deletion_manifest(payload)
        return validate_deletion_manifest_for_event(
            manifest,
            registry=registry,
            current_policy_revision=current_policy_revision,
            actor_id=actor_id,
            authority_grant_id=authority_grant_id,
        )

    return authorize


def load_evidence_store_registry(path: Path, schemas: SchemaRegistry) -> EvidenceStoreRegistry:
    """Load and schema-validate an evidence-store registry configuration file.

    Args:
        path: Path to a YAML (or JSON, a YAML subset) evidence-store
            registry document.
        schemas: Schema registry used to validate against
            `ars://evals/evidence-store-registry` before any field is
            trusted.

    Returns:
        The constructed `EvidenceStoreRegistry`.

    Raises:
        ConfigurationError: If the file cannot be read or parsed, or does
            not contain an object.
        SchemaError: If the parsed document fails schema validation.
    """
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"invalid evidence store registry: {path}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("evidence store registry must be an object")
    schemas.validate("ars://evals/evidence-store-registry", payload)
    return EvidenceStoreRegistry(
        store_id=payload["store_id"],
        registry_hash=payload["registry_hash"],
        policy_revision=payload["policy_revision"],
        primary_root=Path(payload["primary_root"]),
        runtime_root=Path(payload["runtime_root"]),
        staging_root=Path(payload["staging_root"]),
        temp_root=Path(payload["temp_root"]),
        replicas=tuple(Path(item) for item in payload["replicas"]),
        backup_roots=tuple(Path(item) for item in payload["backup_roots"]),
        restore_roots=tuple(Path(item) for item in payload["restore_roots"]),
        permitted_consumers=tuple(payload["permitted_consumers"]),
        retention_policy_ids=tuple(payload["retention_policy_ids"]),
        verifier_authority_bindings=tuple(tuple(pair) for pair in payload["verifier_authority_bindings"]),
        unregistered_replicas_prohibited=payload["unregistered_replicas_prohibited"],
    )
