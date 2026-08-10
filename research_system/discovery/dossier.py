"""Pure, fail-closed preparation of a Discovery dossier admission batch.

The preparer deliberately performs no persistence.  A runtime may append the returned
events atomically after applying its own stream/version and authority fences.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


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
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def accepted_expected_set_hash(expected_set: AcceptedExpectedSet) -> str:
    """Bind every immutable expected-side field except the digest itself."""

    value = asdict(expected_set)
    value.pop("content_hash")
    return _canonical_hash(value)


def _validate_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise DossierAdmissionRejected(f"invalid_{label}")


def _unique_members(members: Iterable[DossierMember], side: str) -> dict[str, DossierMember]:
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

    root_path = root.path.resolve(strict=True)
    candidate = root_path.joinpath(*relative.parts)
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise DossierAdmissionRejected("path_escape") from exc

    current = root_path
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise DossierAdmissionRejected("unregistered_path_alias")
    try:
        raw = candidate.read_bytes()
    except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
        raise DossierAdmissionRejected("incomplete_package") from exc
    return raw


def prepare_dossier_admission(
    *,
    expected_set: AcceptedExpectedSet,
    current_expected_set_revision: int,
    candidate_members: tuple[DossierMember, ...],
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
    for member in expected_set.members:
        _validate_sha256(member.sha256, "member_hash")
        _validate_sha256(member.provenance_hash, "provenance_hash")
        if member.provenance_revision < 1:
            raise DossierAdmissionRejected("stale_provenance_revision")
        raw = _open_registered_member(member, registered_roots)
        digest = hashlib.sha256(raw).hexdigest()
        if len(raw) != member.size_bytes or digest != member.sha256:
            raise DossierAdmissionRejected("member_content_tampered")
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
    package_member = expected[package_rows[0]["member_key"]]
    package_raw = _open_registered_member(package_member, registered_roots)
    try:
        package = json.loads(package_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DossierAdmissionRejected("invalid_package_index") from exc
    if (
        package.get("package_id") != expected_set.package_id
        or package.get("package_version") != expected_set.package_version
    ):
        raise DossierAdmissionRejected("stale_package_identity")
    if package.get("execution_authorized") is not False or package.get("dispatchable") is not False:
        raise DossierAdmissionRejected("provider_execution_boundary_violated")

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
        "ownership_effect": "successor_owned_new_objects_only",
        "provider_execution": "forbidden",
    }
    events: list[dict[str, Any]] = [{"event_type": "ResearchDossierAdmitted", "payload": base}]
    events.extend(
        {"event_type": "PortfolioObjectRegistered", "payload": {**row, "dossier_id": expected_set.dossier_id}}
        for row in observed
        if row["member_kind"] != "scope_definition"
    )
    events.extend(
        {"event_type": "ScopeDefinitionRegistered", "payload": {**row, "dossier_id": expected_set.dossier_id}}
        for row in observed
        if row["member_kind"] == "scope_definition"
    )
    return PreparedDossierAdmission(tuple(events), tuple(observed), closure_hash)
