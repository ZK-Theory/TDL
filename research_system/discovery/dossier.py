"""Pure, fail-closed preparation of a Discovery dossier admission batch.

The preparer deliberately performs no persistence.  A runtime may append the returned
events atomically after applying its own stream/version and authority fences.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Iterable, Mapping

from research_system.store.lock import _open_directory_anchor


class DossierAdmissionRejected(ValueError):
    """The dossier did not match the independently accepted admission subject."""


@dataclass(frozen=True)
class RegisteredRoot:
    root_id: str
    path: Path
    registration_revision: int
    registration_hash: str
    authorized: bool = True


@dataclass(frozen=True)
class DossierMember:
    member_key: str
    member_kind: str
    root_id: str
    relative_path: str
    size_bytes: int
    sha256: str
    provenance_id: str
    provenance_revision: int
    provenance_hash: str


@dataclass(frozen=True)
class AcceptedExpectedSet:
    expected_set_id: str
    revision: int
    content_hash: str
    dossier_id: str
    package_id: str
    package_version: str
    project_id: str
    admission_profile_id: str
    admission_profile_revision: int
    admission_profile_hash: str
    members: tuple[DossierMember, ...]


@dataclass(frozen=True)
class PreparedDossierAdmission:
    events: tuple[dict[str, Any], ...]
    observed_members: tuple[dict[str, Any], ...]
    closure_hash: str


def _canonical_hash(value: Any) -> str:
    """Hash one JSON-compatible value canonically."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def accepted_expected_set_hash(expected_set: AcceptedExpectedSet) -> str:
    """Bind every immutable expected-side field except the digest itself."""

    value = asdict(expected_set)
    value.pop("content_hash")
    return _canonical_hash(value)


def admission_profile_hash(profile_id: str, revision: int) -> str:
    """Bind the provider-free, non-dispatchable WP6.6 admission policy."""

    return _canonical_hash(
        {
            "admission_profile_id": profile_id,
            "admission_profile_revision": revision,
            "dispatchable": False,
            "provider_execution": "forbidden",
        }
    )


def _lexical_normalized_path(path: Path) -> str:
    """Normalize dot segments without resolving links or junctions."""

    return os.path.normpath(os.path.abspath(path)).casefold()


def registered_root_identity_hash(path: Path) -> str:
    """Hash the held physical directory identity and final path."""

    anchor = _open_directory_anchor(path, reject_reparse=False, delete_protect=True)
    try:
        return _canonical_hash(
            {
                "scheme": anchor.identity.scheme,
                "volume_or_device": anchor.identity.volume_or_device,
                "file_id": anchor.identity.file_id.hex(),
                "final_path": str(anchor.final_path).casefold(),
                "registered_path": _lexical_normalized_path(path),
            }
        )
    finally:
        anchor.close()


def _after_root_identity_check(_path: Path) -> None:
    """Fault-injection boundary after identity verification and before read."""


def _after_member_identity_check(_path: Path) -> None:
    """Fault-injection boundary after member identity capture and before open."""


def _assert_live_root(anchor: Any, path: Path) -> None:
    """Require the live root path to retain the held physical identity."""
    observer = _open_directory_anchor(path, reject_reparse=False, delete_protect=False)
    try:
        if observer.identity != anchor.identity or observer.final_path != anchor.final_path:
            raise DossierAdmissionRejected("path_registration_identity_changed")
    finally:
        observer.close()


def _validate_sha256(value: str, label: str) -> None:
    """Reject a malformed lowercase SHA-256 identity."""
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise DossierAdmissionRejected(f"invalid_{label}")


def _unique_members(members: Iterable[DossierMember], side: str) -> dict[str, DossierMember]:
    """Index members while rejecting duplicate keys and paths."""
    by_key: dict[str, DossierMember] = {}
    paths: set[tuple[str, str]] = set()
    for member in members:
        path_identity = (member.root_id, member.relative_path.casefold())
        if member.member_key in by_key:
            raise DossierAdmissionRejected(f"duplicate_{side}_member_key")
        if path_identity in paths:
            raise DossierAdmissionRejected(f"duplicate_{side}_path")
        by_key[member.member_key] = member
        paths.add(path_identity)
    return by_key


def _open_registered_member(member: DossierMember, roots: Mapping[str, RegisteredRoot]) -> bytes:
    """Read one member through its deletion-protected registered root."""
    root = roots.get(member.root_id)
    if root is None:
        raise DossierAdmissionRejected("unregistered_root")
    if not root.authorized:
        raise DossierAdmissionRejected("unauthorized_path")
    if root.registration_revision < 1:
        raise DossierAdmissionRejected("stale_path_registration")
    _validate_sha256(root.registration_hash, "path_registration_hash")

    relative = PurePosixPath(member.relative_path.replace("\\", "/"))
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise DossierAdmissionRejected("path_traversal")

    anchor = _open_directory_anchor(root.path, reject_reparse=False, delete_protect=True)
    try:
        identity_hash = _canonical_hash(
            {
                "scheme": anchor.identity.scheme,
                "volume_or_device": anchor.identity.volume_or_device,
                "file_id": anchor.identity.file_id.hex(),
                "final_path": str(anchor.final_path).casefold(),
                "registered_path": _lexical_normalized_path(root.path),
            }
        )
        if identity_hash != root.registration_hash:
            raise DossierAdmissionRejected("path_registration_identity_mismatch")
        _assert_live_root(anchor, root.path)
        try:
            _after_root_identity_check(root.path)
        except OSError as exc:
            raise DossierAdmissionRejected("path_registration_identity_changed") from exc
        root_path = anchor.final_path
        candidate = root_path.joinpath(*relative.parts)
        try:
            candidate.relative_to(root_path)
        except ValueError as exc:
            raise DossierAdmissionRejected("path_escape") from exc

        current = root_path
        for part in relative.parts:
            current = current / part
            try:
                is_alias = current.is_symlink() or current.is_junction()
            except OSError as exc:
                raise DossierAdmissionRejected("incomplete_package") from exc
            if is_alias:
                raise DossierAdmissionRejected("unregistered_path_alias")
        try:
            before = candidate.stat(follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise DossierAdmissionRejected("path_identity_unproven")
            _after_member_identity_check(candidate)
            with candidate.open("rb") as handle:
                opened = os.fstat(handle.fileno())
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                ):
                    raise DossierAdmissionRejected("path_identity_unproven")
                raw = handle.read()
                after = os.fstat(handle.fileno())
            linked = candidate.stat(follow_symlinks=False)
            stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
            if any(getattr(after, field) != getattr(opened, field) for field in stable_fields) or (
                linked.st_dev,
                linked.st_ino,
                linked.st_nlink,
            ) != (opened.st_dev, opened.st_ino, 1):
                raise DossierAdmissionRejected("path_identity_unproven")
        except DossierAdmissionRejected:
            raise
        except (FileNotFoundError, IsADirectoryError, NotADirectoryError) as exc:
            raise DossierAdmissionRejected("incomplete_package") from exc
        except OSError as exc:
            raise DossierAdmissionRejected("path_identity_unproven") from exc
        _assert_live_root(anchor, root.path)
        refreshed_identity, refreshed_path = anchor.refresh()
        if refreshed_identity != anchor.identity or refreshed_path != anchor.final_path:
            raise DossierAdmissionRejected("path_registration_identity_changed")
        return raw
    finally:
        anchor.close()


def prepare_dossier_admission(
    *,
    expected_set: AcceptedExpectedSet,
    current_expected_set_revision: int,
    candidate_members: tuple[DossierMember, ...],
    candidate_manifest: Mapping[str, Any],
    registered_roots: Mapping[str, RegisteredRoot],
    existing_identities: frozenset[str] = frozenset(),
) -> PreparedDossierAdmission:
    """Validate an exact dossier and return its deterministic atomic event batch.

    ``candidate_members`` is intentionally distinct from ``expected_set.members``:
    the accepted side must originate outside the candidate producer.
    """

    _validate_sha256(expected_set.content_hash, "expected_set_hash")
    if accepted_expected_set_hash(expected_set) != expected_set.content_hash:
        raise DossierAdmissionRejected("expected_set_hash_mismatch")
    _validate_sha256(expected_set.admission_profile_hash, "admission_profile_hash")
    if (
        admission_profile_hash(expected_set.admission_profile_id, expected_set.admission_profile_revision)
        != expected_set.admission_profile_hash
    ):
        raise DossierAdmissionRejected("admission_profile_hash_mismatch")
    if expected_set.revision != current_expected_set_revision:
        raise DossierAdmissionRejected("stale_expected_set_revision")
    if not expected_set.members:
        raise DossierAdmissionRejected("incomplete_package")

    expected = _unique_members(expected_set.members, "expected")
    candidate = _unique_members(candidate_members, "candidate")
    if expected.keys() != candidate.keys():
        raise DossierAdmissionRejected("candidate_member_set_mismatch")
    if expected != candidate:
        raise DossierAdmissionRejected("candidate_member_identity_mismatch")

    protected_identities = {
        expected_set.dossier_id,
        expected_set.expected_set_id,
        *(member.provenance_id for member in expected_set.members),
    }
    if protected_identities & existing_identities:
        raise DossierAdmissionRejected("immutable_identity_collision")

    observed: list[dict[str, Any]] = []
    package_raw: bytes | None = None
    for member in expected_set.members:
        _validate_sha256(member.sha256, "member_hash")
        _validate_sha256(member.provenance_hash, "provenance_hash")
        if member.provenance_revision < 1:
            raise DossierAdmissionRejected("stale_provenance_revision")
        raw = _open_registered_member(member, registered_roots)
        digest = hashlib.sha256(raw).hexdigest()
        if len(raw) != member.size_bytes or digest != member.sha256:
            raise DossierAdmissionRejected("member_content_tampered")
        if member.member_kind == "package_index":
            package_raw = raw
        observed.append(
            {
                "member_key": member.member_key,
                "member_kind": member.member_kind,
                "root_id": member.root_id,
                "relative_path": member.relative_path,
                "size_bytes": len(raw),
                "sha256": digest,
                "provenance_id": member.provenance_id,
                "provenance_revision": member.provenance_revision,
                "provenance_hash": member.provenance_hash,
            }
        )

    package_rows = [row for row in observed if row["member_kind"] == "package_index"]
    if len(package_rows) != 1:
        raise DossierAdmissionRejected("incomplete_package")
    if package_raw is None:
        raise DossierAdmissionRejected("incomplete_package")
    try:
        package = json.loads(package_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DossierAdmissionRejected("invalid_package_index") from exc
    if not isinstance(package, dict):
        raise DossierAdmissionRejected("invalid_package_index")
    if (
        package.get("package_id") != expected_set.package_id
        or package.get("package_version") != expected_set.package_version
    ):
        raise DossierAdmissionRejected("stale_package_identity")
    if package.get("execution_authorized") is not False or package.get("dispatchable") is not False:
        raise DossierAdmissionRejected("provider_execution_boundary_violated")
    components = candidate_manifest.get("components")
    sources = candidate_manifest.get("source_dependencies")
    objects = candidate_manifest.get("object_blueprints")
    scopes = candidate_manifest.get("scope_definition_blueprints")
    edges = candidate_manifest.get("dependency_edges")
    relationships = candidate_manifest.get("relationships")
    families = (components, sources, objects, scopes, edges, relationships)
    if (
        candidate_manifest.get("schema_id") != "ars://portfolio/research-dossier-manifest"
        or candidate_manifest.get("schema_version") != "1.0.0"
        or candidate_manifest.get("dossier_logical_id") != expected_set.dossier_id
        or candidate_manifest.get("dossier_revision") != 1
        or candidate_manifest.get("package_version") != expected_set.package_version
        or not all(isinstance(family, list) for family in families)
        or candidate_manifest.get("component_count") != len(components)
        or candidate_manifest.get("source_dependency_count") != len(sources)
        or candidate_manifest.get("object_count") != len(objects)
        or candidate_manifest.get("scope_count") != len(scopes)
        or candidate_manifest.get("edge_count") != len(edges)
        or candidate_manifest.get("relationship_count") != len(relationships)
        or candidate_manifest.get("admission_profile_ref")
        != {
            "id": expected_set.admission_profile_id,
            "record_revision": expected_set.admission_profile_revision,
            "content_hash": expected_set.admission_profile_hash,
        }
    ):
        raise DossierAdmissionRejected("package_manifest_closure_mismatch")
    manifest_preimage = deepcopy(dict(candidate_manifest))
    manifest_closure_hash = manifest_preimage.pop("closure_hash", None)
    if manifest_closure_hash != _canonical_hash(manifest_preimage):
        raise DossierAdmissionRejected("package_manifest_closure_mismatch")

    observed_by_key = {row["member_key"]: row for row in observed}
    component_keys: set[str] = set()
    for row in components:
        if not isinstance(row, dict):
            raise DossierAdmissionRejected("package_manifest_closure_mismatch")
        key = row.get("component_key")
        observed_row = observed_by_key.get(key)
        if (
            not isinstance(key, str)
            or key in component_keys
            or not isinstance(observed_row, dict)
            or observed_row.get("member_kind") != "component"
            or row.get("root_id") != observed_row.get("root_id")
            or row.get("relative_path_or_object_ref") != observed_row.get("relative_path")
            or row.get("size_bytes") != observed_row.get("size_bytes")
            or row.get("sha256") != observed_row.get("sha256")
        ):
            raise DossierAdmissionRejected("package_manifest_closure_mismatch")
        component_keys.add(key)
    source_keys: set[str] = set()
    for row in sources:
        if not isinstance(row, dict):
            raise DossierAdmissionRejected("package_manifest_closure_mismatch")
        key = row.get("source_key")
        observed_row = observed_by_key.get(key)
        if (
            not isinstance(key, str)
            or key in source_keys
            or not isinstance(observed_row, dict)
            or observed_row.get("member_kind") not in {"package_index", "evidence"}
            or row.get("root_id") != observed_row.get("root_id")
            or row.get("relative_path_or_locator") != observed_row.get("relative_path")
            or row.get("size_bytes") != observed_row.get("size_bytes")
            or row.get("sha256") != observed_row.get("sha256")
        ):
            raise DossierAdmissionRejected("package_manifest_closure_mismatch")
        source_keys.add(key)
    if component_keys | source_keys | {
        row["member_key"] for row in observed if row["member_kind"] == "scope_definition"
    } != set(observed_by_key):
        raise DossierAdmissionRejected("package_manifest_closure_mismatch")

    materialized_objects: list[dict[str, Any]] = []
    semantic_keys: dict[str, tuple[str, int, str]] = {}
    record_ids: set[str] = set()
    for row in objects:
        if not isinstance(row, dict):
            raise DossierAdmissionRejected("invalid_object_blueprint")
        key = row.get("object_key")
        record_id = row.get("proposed_record_id")
        source_keys_for_object = row.get("source_keys")
        preimage = {
            name: deepcopy(value)
            for name, value in row.items()
            if name not in {"blueprint_hash", "expected_content_hash"}
        }
        digest = _canonical_hash(preimage)
        if (
            not isinstance(key, str)
            or key in semantic_keys
            or key not in component_keys
            or not isinstance(record_id, str)
            or record_id in record_ids
            or row.get("proposed_revision") != 1
            or row.get("blueprint_hash") != digest
            or row.get("expected_content_hash") != digest
            or not isinstance(source_keys_for_object, list)
            or not source_keys_for_object
            or not all(isinstance(source_key, str) for source_key in source_keys_for_object)
            or not set(source_keys_for_object).issubset(component_keys | source_keys)
        ):
            raise DossierAdmissionRejected("invalid_object_blueprint")
        semantic_keys[key] = (record_id, 1, digest)
        record_ids.add(record_id)
        materialized_objects.append(
            {
                "record_id": record_id,
                "record_revision": 1,
                "content_sha256": digest,
                "portfolio_kind": row.get("portfolio_kind"),
                "blueprint": deepcopy(row),
                "dossier_id": expected_set.dossier_id,
            }
        )
    if set(semantic_keys) != component_keys:
        raise DossierAdmissionRejected("invalid_object_blueprint")

    materialized_scopes: list[dict[str, Any]] = []
    scope_keys: set[str] = set()
    for row in scopes:
        if not isinstance(row, dict):
            raise DossierAdmissionRejected("invalid_scope_blueprint")
        key = row.get("scope_key")
        scope_id = row.get("proposed_scope_id")
        governing_object_keys = row.get("governing_object_keys")
        preimage = {
            name: deepcopy(value)
            for name, value in row.items()
            if name not in {"blueprint_hash", "expected_content_hash"}
        }
        digest = _canonical_hash(preimage)
        if (
            not isinstance(key, str)
            or key in semantic_keys
            or key in scope_keys
            or not isinstance(scope_id, str)
            or scope_id in record_ids
            or row.get("proposed_revision") != 1
            or row.get("blueprint_hash") != digest
            or row.get("expected_content_hash") != digest
            or not isinstance(governing_object_keys, list)
            or not all(isinstance(object_key, str) for object_key in governing_object_keys)
            or set(governing_object_keys) != component_keys
        ):
            raise DossierAdmissionRejected("invalid_scope_blueprint")
        semantic_keys[key] = (scope_id, 1, digest)
        scope_keys.add(key)
        record_ids.add(scope_id)
        materialized_scopes.append(
            {
                "scope_id": scope_id,
                "scope_revision": 1,
                "content_sha256": digest,
                "blueprint": deepcopy(row),
                "dossier_id": expected_set.dossier_id,
            }
        )
    if not materialized_scopes:
        raise DossierAdmissionRejected("invalid_scope_blueprint")

    materialized_edges: list[dict[str, Any]] = []
    adjacency: dict[str, set[str]] = {key: set() for key in semantic_keys}
    edge_keys: set[str] = set()
    for row in edges:
        if not isinstance(row, dict):
            raise DossierAdmissionRejected("invalid_dependency_edge")
        key = row.get("edge_key")
        edge_id = row.get("proposed_edge_id")
        from_ref = row.get("from_key")
        to_ref = row.get("to_key")
        preimage = {name: deepcopy(value) for name, value in row.items() if name != "expected_content_hash"}
        digest = _canonical_hash(preimage)
        if (
            not isinstance(key, str)
            or key in edge_keys
            or not isinstance(edge_id, str)
            or edge_id in record_ids
            or row.get("proposed_revision") != 1
            or not isinstance(from_ref, dict)
            or not isinstance(to_ref, dict)
            or from_ref.get("key") not in component_keys
            or to_ref.get("key") not in component_keys
            or from_ref.get("key") == to_ref.get("key")
            or tuple((from_ref.get("key"), from_ref.get("revision"), from_ref.get("content_hash")))
            != (from_ref.get("key"), *semantic_keys[from_ref.get("key")][1:])
            or tuple((to_ref.get("key"), to_ref.get("revision"), to_ref.get("content_hash")))
            != (to_ref.get("key"), *semantic_keys[to_ref.get("key")][1:])
            or row.get("effective_scope_key") not in scope_keys
            or row.get("expected_content_hash") != digest
        ):
            raise DossierAdmissionRejected("invalid_dependency_edge")
        edge_keys.add(key)
        record_ids.add(edge_id)
        if row.get("required"):
            adjacency[from_ref["key"]].add(to_ref["key"])
        materialized_edges.append(
            {
                "record_id": edge_id,
                "record_revision": 1,
                "content_sha256": digest,
                "portfolio_kind": "dependency_edge",
                "blueprint": deepcopy(row),
                "dossier_id": expected_set.dossier_id,
            }
        )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise DossierAdmissionRejected("dependency_cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in adjacency[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in adjacency:
        visit(node)

    relationship_keys: set[str] = set()
    for row in relationships:
        if not isinstance(row, dict):
            raise DossierAdmissionRejected("invalid_relationship")
        key = row.get("relationship_key")
        members = row.get("ordered_member_keys_with_revisions_hashes")
        if (
            not isinstance(key, str)
            or key in relationship_keys
            or not isinstance(members, list)
            or not members
            or any(
                not isinstance(member, dict)
                or member.get("key") not in semantic_keys
                or (member.get("revision"), member.get("content_hash")) != semantic_keys[member.get("key")][1:]
                for member in members
            )
            or row.get("relation_hash") != _canonical_hash(members)
        ):
            raise DossierAdmissionRejected("invalid_relationship")
        relationship_keys.add(key)
    if not relationships or any(
        {member["key"] for member in row["ordered_member_keys_with_revisions_hashes"]} != set(semantic_keys)
        for row in relationships
    ):
        raise DossierAdmissionRejected("invalid_relationship")

    if protected_identities & record_ids:
        raise DossierAdmissionRejected("immutable_identity_collision")
    protected_identities.update(record_ids)
    if protected_identities & existing_identities:
        raise DossierAdmissionRejected("immutable_identity_collision")

    closure_hash = _canonical_hash(observed)
    base = {
        "dossier_id": expected_set.dossier_id,
        "project_id": expected_set.project_id,
        "package_id": expected_set.package_id,
        "package_version": expected_set.package_version,
        "expected_set_id": expected_set.expected_set_id,
        "expected_set_revision": expected_set.revision,
        "expected_set_hash": expected_set.content_hash,
        "admission_profile_id": expected_set.admission_profile_id,
        "admission_profile_revision": expected_set.admission_profile_revision,
        "admission_profile_hash": expected_set.admission_profile_hash,
        "member_count": len(observed),
        "member_closure_hash": closure_hash,
        "candidate_manifest_hash": _canonical_hash(candidate_manifest),
        "object_count": len(materialized_objects),
        "scope_count": len(materialized_scopes),
        "edge_count": len(materialized_edges),
        "relationship_count": len(relationships),
        "relationships": deepcopy(relationships),
        "ownership_effect": "successor_owned_new_objects_only",
        "provider_execution": "forbidden",
    }
    events: list[dict[str, Any]] = [{"event_type": "ResearchDossierAdmitted", "payload": base}]
    events.extend(
        {"event_type": "PortfolioObjectRegistered", "payload": row}
        for row in (*materialized_objects, *materialized_edges)
    )
    events.extend({"event_type": "ScopeDefinitionRegistered", "payload": row} for row in materialized_scopes)
    return PreparedDossierAdmission(tuple(events), tuple(observed), closure_hash)
