"""Accepted R1/R2 policy and evidence-derived deletion verification."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import yaml

from research_system.canonical import canonical_bytes, jsonable, sha256_hex
from research_system.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class RetentionRule:
    max_days: int
    review_lead_days: int
    owner: str
    extension_authority: str
    anchor: str
    use_earlier_source_expiry: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceStoreRegistry:
    store_id: str
    registry_hash: str
    policy_revision: str
    primary_root: Path
    runtime_root: Path
    staging_root: Path
    temp_root: Path
    replicas: tuple[Path, ...]
    permitted_consumers: tuple[str, ...]
    retention_policy_ids: tuple[str, ...]
    verifier_authority_bindings: tuple[tuple[str, str], ...]
    unregistered_replicas_prohibited: bool
    backup_roots: tuple[Path, ...] = ()
    restore_roots: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        if not self.verifier_authority_bindings:
            raise ValueError("verifier authority bindings must not be empty")
        if len(set(self.verifier_authority_bindings)) != len(
            self.verifier_authority_bindings
        ):
            raise ValueError("verifier authority bindings must be unique")
        if any(
            not actor_id or not grant_id
            for actor_id, grant_id in self.verifier_authority_bindings
        ):
            raise ValueError("verifier authority binding values must not be empty")

    def checked_locations(self) -> tuple[Path, ...]:
        """Derive the complete location set; callers cannot narrow it."""
        locations = (
            self.primary_root,
            self.runtime_root,
            self.staging_root,
            self.temp_root,
            *self.replicas,
            *self.backup_roots,
            *self.restore_roots,
        )
        resolved = tuple(path.resolve(strict=False) for path in locations)
        if len(resolved) != len(set(resolved)):
            raise ValueError("evidence registry contains duplicate locations")
        return resolved


@dataclass(frozen=True, slots=True)
class LocationInspection:
    resolved_path: str
    absent: bool
    evidence_hash: str
    inspection_hash: str
    inaccessible: bool
    reparse_target: str | None


@dataclass(frozen=True, slots=True)
class CanonicalPayloadScan:
    payload_present: bool
    scan_hash: str


@dataclass(frozen=True, slots=True)
class DeletionVerificationManifest:
    evidence_id: str
    evidence_hash: str
    retention_rule_id: str
    policy_revision: str
    registry_hash: str
    actor_id: str
    authority_grant_id: str
    checked_locations: tuple[LocationInspection, ...]
    unregistered_replicas: tuple[str, ...]
    inaccessible_locations: tuple[str, ...]
    reparse_locations: tuple[tuple[str, str], ...]
    canonical_payload_present: bool
    canonical_scan_hash: str
    authority_current: bool
    verified_at: str
    status: str
    manifest_hash: str


RULES = {
    ("R1", "redacted_command_summary"): RetentionRule(
        180, 30, "system_maintainer", "manager", "run_terminal"
    ),
    ("R1", "operational_measurement"): RetentionRule(
        365, 30, "system_maintainer", "manager", "release_decision"
    ),
    ("R1", "grader_explanation"): RetentionRule(
        365, 30, "evaluation_owner", "manager", "release_decision"
    ),
    ("R2", "restricted_local_reference"): RetentionRule(
        90,
        14,
        "data_controller",
        "data_authority",
        "run_terminal",
        True,
    ),
    ("R2", "minimized_sensitive_excerpt"): RetentionRule(
        30,
        7,
        "data_controller",
        "data_authority",
        "run_terminal",
        True,
    ),
}


def require_retention_rule(retention_class: str, evidence_type: str) -> RetentionRule:
    """Return the accepted rule or fail closed; R3 is never storable."""
    if retention_class == "R3":
        raise ValueError("R3_prohibited")
    try:
        return RULES[(retention_class, evidence_type)]
    except KeyError as exc:
        raise ValueError("retention_rule_missing") from exc


# R0 covers repo-resident synthetic packages: no expiring payload, no retention
# rule, permanently committed (05-plan §7 — canonical records retain only R0
# identity/hash). It therefore has no ``RULES`` entry and its rule id is fixed.
R0_RETENTION_RULE_IDS = frozenset({"R0:synthetic_fixture_package"})


def validate_fixture_retention(retention_class: str, retention_rule_id: str) -> None:
    """Cross-check a staged fixture's declared retention labels against policy.

    R0 packages must name a known R0 rule id and carry no expiring rule; R1/R2
    must name an accepted ``RULES`` rule as ``"<class>:<evidence_type>"``; R3 is
    never storable.

    Args:
        retention_class: Declared retention class (``R0``/``R1``/``R2``).
        retention_rule_id: Declared ``"<class>:<evidence_type>"`` rule id.

    Raises:
        ValueError: If the class is R3, an R0 rule id is unknown, or an R1/R2
            rule id does not resolve to an accepted rule.
    """
    if retention_class == "R3":
        raise ValueError("R3_prohibited")
    if retention_class == "R0":
        if retention_rule_id not in R0_RETENTION_RULE_IDS:
            raise ValueError("unknown_r0_retention_rule")
        return
    prefix, _, evidence_type = retention_rule_id.partition(":")
    if prefix != retention_class or not evidence_type:
        raise ValueError("retention_rule_id_class_mismatch")
    require_retention_rule(retention_class, evidence_type)


def _manifest_hash(manifest: DeletionVerificationManifest) -> str:
    payload = asdict(manifest)
    payload["manifest_hash"] = ""
    return sha256_hex(canonical_bytes(jsonable(payload)))


def verify_deletion(
    *,
    evidence_id: str,
    evidence_hash: str,
    retention_rule_id: str,
    registry: EvidenceStoreRegistry,
    inspect_location: Callable[[Path, str], LocationInspection],
    discover_replicas: Callable[[EvidenceStoreRegistry], Iterable[Path]],
    canonical_payload_scan: Callable[[str], CanonicalPayloadScan],
    actor_id: str,
    authority_grant_id: str,
    verified_at: str,
) -> DeletionVerificationManifest:
    """Inspect every authorized location and derive, rather than accept, status."""
    if retention_rule_id not in registry.retention_policy_ids:
        raise ValueError("retention_rule_not_authorized_for_store")
    inspections = []
    for path in registry.checked_locations():
        inspection = inspect_location(path, evidence_hash)
        if not isinstance(inspection, LocationInspection):
            raise TypeError("inspect_location must return LocationInspection")
        if Path(inspection.resolved_path) != path:
            raise ValueError("inspection path does not match registry location")
        if inspection.evidence_hash != evidence_hash:
            raise ValueError("inspection evidence hash mismatch")
        if not inspection.inspection_hash:
            raise ValueError("inspection evidence hash is required")
        inspections.append(inspection)

    discovered = {path.resolve(strict=False) for path in discover_replicas(registry)}
    registered = {
        path.resolve(strict=False)
        for path in (*registry.replicas, *registry.backup_roots, *registry.restore_roots)
    }
    unregistered = tuple(sorted(str(path) for path in discovered - registered))
    canonical_scan = canonical_payload_scan(evidence_hash)
    if not isinstance(canonical_scan, CanonicalPayloadScan):
        raise TypeError("canonical_payload_scan must return CanonicalPayloadScan")
    inaccessible = tuple(
        inspection.resolved_path
        for inspection in inspections
        if inspection.inaccessible
    )
    reparse = tuple(
        (inspection.resolved_path, str(inspection.reparse_target))
        for inspection in inspections
        if inspection.reparse_target is not None
    )
    authority_current = (
        actor_id,
        authority_grant_id,
    ) in registry.verifier_authority_bindings
    verified = (
        all(inspection.absent for inspection in inspections)
        and not inaccessible
        and not reparse
        and not unregistered
        and not canonical_scan.payload_present
        and bool(canonical_scan.scan_hash)
        and authority_current
        and registry.unregistered_replicas_prohibited
    )
    manifest = DeletionVerificationManifest(
        evidence_id=evidence_id,
        evidence_hash=evidence_hash,
        retention_rule_id=retention_rule_id,
        policy_revision=registry.policy_revision,
        registry_hash=registry.registry_hash,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
        checked_locations=tuple(inspections),
        unregistered_replicas=unregistered,
        inaccessible_locations=inaccessible,
        reparse_locations=reparse,
        canonical_payload_present=canonical_scan.payload_present,
        canonical_scan_hash=canonical_scan.scan_hash,
        authority_current=authority_current,
        verified_at=verified_at,
        status="verified" if verified else "deletion_pending",
        manifest_hash="",
    )
    return replace(manifest, manifest_hash=_manifest_hash(manifest))


def validate_deletion_manifest_for_event(
    manifest: DeletionVerificationManifest,
    *,
    registry: EvidenceStoreRegistry,
    current_policy_revision: str,
    actor_id: str,
    authority_grant_id: str,
) -> dict[str, object]:
    """Authorize only a complete, current, evidence-derived verified event."""
    if manifest.manifest_hash != _manifest_hash(manifest):
        raise ValueError("deletion manifest hash mismatch")
    if manifest.status != "verified":
        raise ValueError("deletion_pending cannot authorize verified event")
    if (
        manifest.registry_hash != registry.registry_hash
        or manifest.policy_revision != current_policy_revision
    ):
        raise ValueError("stale deletion registry or policy")
    if (
        manifest.actor_id != actor_id
        or manifest.authority_grant_id != authority_grant_id
        or not manifest.authority_current
        or (actor_id, authority_grant_id) not in registry.verifier_authority_bindings
    ):
        raise ValueError("deletion verifier authority mismatch")
    expected_paths = {str(path) for path in registry.checked_locations()}
    observed_paths = {
        inspection.resolved_path for inspection in manifest.checked_locations
    }
    if expected_paths != observed_paths:
        raise ValueError("deletion checked-location closure mismatch")
    if (
        any(
            not inspection.absent
            or inspection.inaccessible
            or inspection.reparse_target is not None
            for inspection in manifest.checked_locations
        )
        or manifest.unregistered_replicas
        or manifest.inaccessible_locations
        or manifest.reparse_locations
        or manifest.canonical_payload_present
    ):
        raise ValueError("deletion manifest is not complete")
    return {
        "evidence_store_id": registry.store_id,
        "evidence_id": manifest.evidence_id,
        "evidence_hash": manifest.evidence_hash,
        "retention_rule_id": manifest.retention_rule_id,
        "policy_revision": manifest.policy_revision,
        "registry_hash": manifest.registry_hash,
        "actor_id": manifest.actor_id,
        "authority_grant_id": manifest.authority_grant_id,
        "checked_locations": [
            {
                "resolved_path": inspection.resolved_path,
                "inspection_hash": inspection.inspection_hash,
            }
            for inspection in manifest.checked_locations
        ],
        "canonical_scan_hash": manifest.canonical_scan_hash,
        "verified_at": manifest.verified_at,
        "status": "verified",
        "manifest_hash": manifest.manifest_hash,
    }


def validate_retention_policy(path: Path) -> dict[str, object]:
    """Validate the tracked accepted policy against the exact owner decision."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"invalid retention policy: {path}") from exc
    if not isinstance(payload, dict) or payload.get("policy_revision") != (
        "p0-retention-v1"
    ):
        raise ConfigurationError("invalid retention policy revision")
    rows = payload.get("rules")
    if not isinstance(rows, list):
        raise ConfigurationError("retention policy rules must be a list")
    observed = {
        (row.get("retention_class"), row.get("evidence_type")): row
        for row in rows
        if isinstance(row, dict)
    }
    if set(observed) != set(RULES):
        raise ConfigurationError("retention policy rule closure mismatch")
    for key, rule in RULES.items():
        row = observed[key]
        expected = {
            "max_days": rule.max_days,
            "review_lead_days": rule.review_lead_days,
            "owner": rule.owner,
            "extension_authority": rule.extension_authority,
            "anchor": rule.anchor,
            "use_earlier_source_expiry": rule.use_earlier_source_expiry,
        }
        if any(row.get(field) != value for field, value in expected.items()):
            raise ConfigurationError(f"retention policy mismatch: {key}")
    if payload.get("r3_storage") != "prohibited":
        raise ConfigurationError("R3 storage must be prohibited")
    if payload.get("unregistered_replicas") != "prohibited":
        raise ConfigurationError("unregistered replicas must be prohibited")
    return payload
