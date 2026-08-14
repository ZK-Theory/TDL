"""Provider-free Gate 6 eligibility certification for the accepted SCALE-01 dossier.

The public functions in this module deliberately prepare no Discovery command and
write no input root.  They validate the already accepted WP6.6 dossier against
an explicit capability-read-only grant, then publish one immutable envelope.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess  # nosec B404 - fixed Git identity commands for accepted inputs
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierAdmissionRejected,
    DossierMember,
    ReadOnlyRootCapability,
    RegisteredRoot,
    accepted_expected_set_hash,
    admission_profile_hash,
    canonical_dossier_hash,
    issue_read_only_root_capability,
    prepare_dossier_admission,
    registered_root_identity_hash,
)
from research_system.errors import ConflictError, IntegrityError


_CONTRACT_PATH = Path(".research-system/contracts/gate6/scale01-eligibility-envelope-contract.json")
_DOSSIER_AUTHORITY_PATH = Path(".research-system/contracts/wp6-6/tda-scale-dossier-expected-set-authority.json")
_PATH_AUTHORITY_PATH = Path(".research-system/contracts/wp6-6/tda-scale-path-registration-authority.json")
_GIT_TIMEOUT_SECONDS = 10


class Gate6EligibilityError(IntegrityError):
    """The Gate 6 preflight has no eligible, immutable result to publish."""


def parse_utc_timestamp(value: str) -> datetime:
    """Parse one strict UTC RFC 3339 instant used by a root grant."""

    if not isinstance(value, str) or not value.endswith("Z"):
        raise Gate6EligibilityError("Gate 6 timestamp must be an RFC 3339 UTC value ending in Z")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise Gate6EligibilityError("Gate 6 timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise Gate6EligibilityError("Gate 6 timestamp must be UTC")
    return parsed.astimezone(UTC)


def _canonical_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Gate6EligibilityError("Gate 6 clock must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(
    path: Path,
    label: str,
    *,
    require_canonical: bool = True,
) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Gate6EligibilityError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise Gate6EligibilityError(f"{label} is not a JSON object: {path}")
    try:
        canonical = canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise Gate6EligibilityError(f"{label} is not canonical JSON: {path}") from exc
    if require_canonical and raw not in {canonical, canonical + b"\n"}:
        raise Gate6EligibilityError(f"{label} is not canonical JSON: {path}")
    return value, raw


def _tracked_canonical_json(
    repository_root: Path,
    relative_path: Path,
    expected_raw_sha256: str,
    label: str,
) -> tuple[dict[str, Any], bytes]:
    path = repository_root / relative_path
    value, raw = _canonical_json(path, label, require_canonical=False)
    if sha256_hex(raw) != expected_raw_sha256:
        raise Gate6EligibilityError(f"{label} raw SHA-256 differs from the eligibility contract")
    _require_current_git_bytes(repository_root, relative_path, raw, label)
    return value, raw


def _require_current_git_bytes(repository_root: Path, relative_path: Path, raw: bytes, label: str) -> None:
    """Bind an accepted input to the exact bytes at the current Git subject."""

    try:
        committed = subprocess.run(  # nosec B603 B607 - fixed repository and path
            ["git", "-C", str(repository_root), "show", f"HEAD:{relative_path.as_posix()}"],
            check=True,
            capture_output=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise Gate6EligibilityError(f"{label} lacks current Git identity") from exc
    if committed != raw:
        raise Gate6EligibilityError(f"{label} differs from its current Git bytes")


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise Gate6EligibilityError(f"invalid {label} fields")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Gate6EligibilityError(f"invalid {label}")
    return value


def _load_contract(repository_root: Path) -> tuple[dict[str, Any], bytes]:
    contract, raw = _canonical_json(
        repository_root / _CONTRACT_PATH,
        "Gate 6 eligibility contract",
        require_canonical=False,
    )
    _require_current_git_bytes(repository_root, _CONTRACT_PATH, raw, "Gate 6 eligibility contract")
    _require_keys(
        contract,
        {"schema_id", "schema_version", "authority", "admission", "root_grant", "schemas", "verdict"},
        "Gate 6 eligibility contract",
    )
    if (
        contract["schema_id"] != "ars://contracts/gate6/scale01-eligibility-envelope-contract"
        or contract["schema_version"] != "1.0.0"
    ):
        raise Gate6EligibilityError("unexpected Gate 6 eligibility contract identity")
    return contract, raw


def _schema_from_contract(
    repository_root: Path,
    contract: Mapping[str, Any],
    name: str,
) -> Draft202012Validator:
    schemas = _require_mapping(contract.get("schemas"), "eligibility schemas")
    declared = _require_mapping(schemas.get(name), f"{name} schema declaration")
    _require_keys(declared, {"schema_id", "schema_version", "repository_path", "raw_sha256"}, f"{name} schema")
    schema_path = declared.get("repository_path")
    if not isinstance(schema_path, str) or Path(schema_path).is_absolute() or ".." in Path(schema_path).parts:
        raise Gate6EligibilityError(f"invalid {name} schema path")
    relative_path = Path(schema_path)
    schema, raw = _canonical_json(repository_root / relative_path, f"{name} schema", require_canonical=False)
    if sha256_hex(raw) != declared.get("raw_sha256"):
        raise Gate6EligibilityError(f"{name} schema differs from the eligibility contract")
    _require_current_git_bytes(repository_root, relative_path, raw, f"{name} schema")
    if schema.get("$id") != declared.get("schema_id"):
        raise Gate6EligibilityError(f"{name} schema identity mismatch")
    try:
        return Draft202012Validator(schema)
    except Exception as exc:  # jsonschema exposes several version-specific schema exceptions
        raise Gate6EligibilityError(f"invalid {name} schema") from exc


def _validate_schema(validator: Draft202012Validator, value: Mapping[str, Any], label: str) -> None:
    try:
        validator.validate(dict(value))
    except ValidationError as exc:
        raise Gate6EligibilityError(f"invalid {label}") from exc


def _load_expected_set(
    repository_root: Path,
    contract: Mapping[str, Any],
) -> tuple[AcceptedExpectedSet, dict[str, str], dict[str, str]]:
    authority = _require_mapping(contract.get("authority"), "eligibility authority")
    dossier_contract = _require_mapping(authority.get("dossier_expected_set"), "dossier authority contract")
    path_contract = _require_mapping(authority.get("path_registration"), "path authority contract")
    _require_keys(
        dossier_contract,
        {
            "repository_path",
            "raw_sha256",
            "content_sha256",
            "expected_set_id",
            "revision",
            "dossier_id",
            "package_id",
            "package_version",
            "manifest_sha256",
            "admission_profile_id",
            "admission_profile_revision",
            "admission_profile_hash",
        },
        "dossier authority contract",
    )
    _require_keys(
        path_contract,
        {"repository_path", "raw_sha256", "content_sha256", "registered_roots"},
        "path authority contract",
    )
    if dossier_contract.get("repository_path") != _DOSSIER_AUTHORITY_PATH.as_posix():
        raise Gate6EligibilityError("unexpected dossier authority path")
    if path_contract.get("repository_path") != _PATH_AUTHORITY_PATH.as_posix():
        raise Gate6EligibilityError("unexpected path authority path")
    dossier_authority, dossier_raw = _tracked_canonical_json(
        repository_root,
        _DOSSIER_AUTHORITY_PATH,
        str(dossier_contract.get("raw_sha256")),
        "accepted WP6.6 dossier authority",
    )
    path_authority, path_raw = _tracked_canonical_json(
        repository_root,
        _PATH_AUTHORITY_PATH,
        str(path_contract.get("raw_sha256")),
        "accepted WP6.6 path authority",
    )
    expected_value = _require_mapping(dossier_authority.get("expected_set"), "accepted expected set")
    try:
        expected = AcceptedExpectedSet(
            **{
                **expected_value,
                "members": tuple(DossierMember(**member) for member in expected_value["members"]),
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise Gate6EligibilityError("accepted expected set is malformed") from exc
    required_expected = {
        "expected_set_id": expected.expected_set_id,
        "revision": expected.revision,
        "dossier_id": expected.dossier_id,
        "package_id": expected.package_id,
        "package_version": expected.package_version,
        "manifest_sha256": expected.manifest_sha256,
        "admission_profile_id": expected.admission_profile_id,
        "admission_profile_revision": expected.admission_profile_revision,
        "admission_profile_hash": expected.admission_profile_hash,
    }
    if any(dossier_contract.get(key) != value for key, value in required_expected.items()):
        raise Gate6EligibilityError("accepted expected set differs from the eligibility contract")
    if (
        dossier_authority.get("authority_kind") != "dossier_expected_set"
        or dossier_authority.get("content_sha256") != dossier_contract.get("content_sha256")
        or expected.content_hash != dossier_contract.get("content_sha256")
        or accepted_expected_set_hash(expected) != expected.content_hash
        or admission_profile_hash(expected.admission_profile_id, expected.admission_profile_revision)
        != expected.admission_profile_hash
    ):
        raise Gate6EligibilityError("accepted dossier authority integrity mismatch")
    expected_decision = {
        "dispatchable": False,
        "profile_id": expected.admission_profile_id,
        "profile_revision": expected.admission_profile_revision,
        "provider_execution": "forbidden",
    }
    if dossier_authority.get("admission_profile_decision") != expected_decision:
        raise Gate6EligibilityError("accepted dossier authority is not provider-free and non-dispatchable")
    registered_roots = path_authority.get("registered_roots")
    expected_root_rows = path_contract.get("registered_roots")
    if (
        path_authority.get("authority_kind") != "path_registration"
        or path_authority.get("content_sha256") != path_contract.get("content_sha256")
        or not isinstance(registered_roots, list)
        or not isinstance(expected_root_rows, list)
        or len(registered_roots) != len(expected_root_rows)
    ):
        raise Gate6EligibilityError("accepted path authority integrity mismatch")
    registration_hashes: dict[str, str] = {}
    for declared in expected_root_rows:
        if not isinstance(declared, Mapping):
            raise Gate6EligibilityError("invalid expected root declaration")
        root_id = declared.get("root_id")
        registration_hash = declared.get("registration_hash")
        if not isinstance(root_id, str) or not isinstance(registration_hash, str):
            raise Gate6EligibilityError("invalid expected root declaration")
        actual = next(
            (row for row in registered_roots if isinstance(row, Mapping) and row.get("root_id") == root_id), None
        )
        if (
            not isinstance(actual, Mapping)
            or actual.get("registration_hash") != registration_hash
            or actual.get("registration_revision") != 1
            or actual.get("authorized") is not True
        ):
            raise Gate6EligibilityError("accepted root registration differs from the eligibility contract")
        registration_hashes[root_id] = registration_hash
    if set(registration_hashes) != {"repo", "vault"}:
        raise Gate6EligibilityError("Gate 6 eligibility requires exactly the repo and vault roots")
    return (
        expected,
        registration_hashes,
        {
            "dossier": sha256_hex(dossier_raw),
            "path": sha256_hex(path_raw),
        },
    )


def _resolve_roots(roots: Mapping[str, Path], registration_hashes: Mapping[str, str]) -> dict[str, RegisteredRoot]:
    if set(roots) != {"repo", "vault"}:
        raise Gate6EligibilityError("Gate 6 eligibility requires exactly repo and vault root arguments")
    result: dict[str, RegisteredRoot] = {}
    for root_id in ("repo", "vault"):
        root = roots[root_id]
        if not isinstance(root, Path):
            raise Gate6EligibilityError("Gate 6 root must be a filesystem path")
        try:
            # The accepted vault root is a Windows reparse point.  Its registered
            # identity intentionally includes that lexical mount path, so do not
            # resolve it through the mount before comparing its authority hash.
            root_path = Path(os.path.abspath(root.expanduser()))
            if not root_path.is_dir():
                raise OSError("root is not a directory")
            identity = registered_root_identity_hash(root_path)
        except (OSError, IntegrityError) as exc:
            raise Gate6EligibilityError(f"registered Gate 6 root is unavailable: {root_id}") from exc
        expected_identity = registration_hashes[root_id]
        if identity != expected_identity:
            raise Gate6EligibilityError(f"registered Gate 6 root identity mismatch: {root_id}")
        result[root_id] = RegisteredRoot(root_id, root_path, 1, expected_identity, authorized=True)
    return result


def _member_set_hash(expected: AcceptedExpectedSet, root_id: str) -> str:
    members = [asdict(member) for member in expected.members if member.root_id == root_id]
    if not members:
        raise Gate6EligibilityError(f"accepted expected set has no members for root: {root_id}")
    return canonical_dossier_hash(members)


def _resolve_repository_root(repository_root: Path) -> Path:
    """Resolve the candidate repository or fail through the public ARS error path."""

    try:
        return repository_root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise Gate6EligibilityError("Gate 6 repository root is unavailable") from exc


def _require_output_outside_roots(output_path: Path, roots: Mapping[str, RegisteredRoot], label: str) -> Path:
    lexical_candidate = Path(os.path.abspath(output_path.expanduser()))
    candidate = lexical_candidate.resolve(strict=False)
    for root in roots.values():
        root_paths = (Path(os.path.abspath(root.path)), root.path.resolve(strict=True))
        for candidate_path in (lexical_candidate, candidate):
            for root_path in root_paths:
                try:
                    candidate_path.relative_to(root_path)
                except ValueError:
                    continue
                raise Gate6EligibilityError(f"{label} must be outside every governed input root")
    return candidate


def _issue_read_only_capabilities(
    grant: Mapping[str, Any],
    registered_roots: Mapping[str, RegisteredRoot],
) -> dict[str, ReadOnlyRootCapability]:
    """Turn one validated grant into the only read authority used for admission."""

    if grant.get("enforcement") != "capability_read_only" or grant.get("allowed_operations") != [
        "read_registered_member"
    ]:
        raise Gate6EligibilityError("root grant lacks the read-only capability policy")
    try:
        return {root_id: issue_read_only_root_capability(registered_roots[root_id]) for root_id in ("repo", "vault")}
    except (KeyError, DossierAdmissionRejected) as exc:
        raise Gate6EligibilityError("root grant cannot issue the read-only capabilities") from exc


def _immutable_publish(path: Path, value: Mapping[str, Any], label: str) -> dict[str, Any]:
    raw = canonical_bytes(dict(value))
    if path.exists():
        existing, existing_raw = _canonical_json(path, label)
        if existing_raw != raw:
            raise ConflictError(f"{label} already exists with different immutable bytes")
        return existing
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.urandom(12).hex()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            existing, existing_raw = _canonical_json(path, label)
            if existing_raw != raw:
                raise ConflictError(f"{label} already exists with different immutable bytes")
            return existing
    except OSError as exc:
        raise Gate6EligibilityError(f"cannot publish immutable {label}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return dict(value)


def _candidate_manifest(expected: AcceptedExpectedSet) -> dict[str, Any]:
    """Reconstruct the fixed WP6.6 candidate only from its accepted expected subject."""

    component_members = [member for member in expected.members if member.member_kind == "component"]
    source_members = [member for member in expected.members if member.member_kind in {"package_index", "evidence"}]
    if not component_members or component_members[0].member_key != "MASTER-PROGRAMME":
        raise Gate6EligibilityError("accepted SCALE-01 component ordering is invalid")
    components = [
        {
            "component_key": member.member_key,
            "component_kind": "immutable_programme_source",
            "schema_id": "ars://portfolio/source-component",
            "schema_version": "1.0.0",
            "root_id": member.root_id,
            "relative_path_or_object_ref": member.relative_path,
            "size_bytes": member.size_bytes,
            "sha256": member.sha256,
            "required": True,
            "dependency_keys": [],
            "permitted_consumers": ["portfolio-admission"],
            "confidentiality_class": "internal",
        }
        for member in component_members
    ]
    sources = [
        {
            "source_key": member.member_key,
            "source_kind": member.member_kind,
            "schema_or_media_type": "application/json",
            "root_id": member.root_id,
            "relative_path_or_locator": member.relative_path,
            "size_bytes": member.size_bytes,
            "sha256": member.sha256,
            "source_authority_class": "independently_observed",
            "required": True,
            "permitted_consumers": ["portfolio-admission"],
            "confidentiality_class": "internal",
            "independent_resolution_policy_id": "policy:wp6.6:registered-path-read",
            "independent_resolution_policy_hash": "7" * 64,
        }
        for member in source_members
    ]
    objects: list[dict[str, Any]] = []
    object_refs: dict[str, dict[str, Any]] = {}
    for index, member in enumerate(component_members, start=1):
        row: dict[str, Any] = {
            "object_key": member.member_key,
            "portfolio_kind": "programme" if member.member_key == "MASTER-PROGRAMME" else "candidate_definition",
            "schema_id": "ars://portfolio/object",
            "schema_version": "1.0.0",
            "proposed_record_id": f"obj_019fed25-b33e-7740-b280-{1000 + index:012d}",
            "proposed_revision": 1,
            "source_keys": [member.member_key],
            "permitted_consumers": ["portfolio-catalogue"],
        }
        digest = canonical_dossier_hash(row)
        row.update(blueprint_hash=digest, expected_content_hash=digest)
        objects.append(row)
        object_refs[member.member_key] = {"key": member.member_key, "revision": 1, "content_hash": digest}
    scope_row: dict[str, Any] = {
        "scope_key": "tda-scale-programme",
        "scope_schema_id": "ars://portfolio/scope-definition",
        "scope_schema_version": "1.0.0",
        "proposed_scope_id": "obj_019fed25-b33e-7740-b280-000000001999",
        "proposed_revision": 1,
        "governing_object_keys": [member.member_key for member in component_members],
        "permitted_consumers": ["portfolio-catalogue"],
    }
    scope_digest = canonical_dossier_hash(scope_row)
    scope_row.update(blueprint_hash=scope_digest, expected_content_hash=scope_digest)
    scope_ref = {"key": "tda-scale-programme", "revision": 1, "content_hash": scope_digest}
    edges: list[dict[str, Any]] = []
    master = component_members[0]
    for index, member in enumerate(component_members[1:], start=1):
        edge: dict[str, Any] = {
            "edge_key": f"{master.member_key}-contains-{member.member_key}",
            "edge_type": "contains",
            "proposed_edge_id": f"obj_019fed25-b33e-7740-b280-{2000 + index:012d}",
            "proposed_revision": 1,
            "from_key": object_refs[master.member_key],
            "to_key": object_refs[member.member_key],
            "required": True,
            "satisfaction_predicate_ref_or_null": None,
            "effective_scope_key": "tda-scale-programme",
        }
        edge["expected_content_hash"] = canonical_dossier_hash(edge)
        edges.append(edge)
    relationship_members = deepcopy([*object_refs.values(), scope_ref])
    manifest: dict[str, Any] = {
        "schema_id": "ars://portfolio/research-dossier-manifest",
        "schema_version": "1.0.0",
        "dossier_logical_id": expected.dossier_id,
        "dossier_revision": 1,
        "package_version": expected.package_version,
        "purpose": "Provider-free admission of the exact TDA-scale programme dossier.",
        "author": "WP6.6 Portfolio Steward",
        "created_at": "2026-08-01T00:00:00Z",
        "governing_decisions": [],
        "component_count": len(components),
        "components": components,
        "source_dependency_count": len(sources),
        "source_dependencies": sources,
        "object_blueprints": objects,
        "scope_definition_blueprints": [scope_row],
        "dependency_edges": edges,
        "relationships": [
            {
                "relationship_key": "tda-scale-programme-closure",
                "relationship_kind": "contains",
                "ordered_member_keys_with_revisions_hashes": relationship_members,
                "relation_schema_id": "ars://portfolio/relation/dossier-six-family-closure",
                "relation_schema_version": "1.0.0",
                "relation_hash": canonical_dossier_hash(relationship_members),
            }
        ],
        "object_count": len(objects),
        "scope_count": 1,
        "edge_count": len(edges),
        "relationship_count": 1,
        "admission_profile_ref": {
            "id": expected.admission_profile_id,
            "record_revision": expected.admission_profile_revision,
            "content_hash": expected.admission_profile_hash,
        },
        "ownership_declarations": ["Successor owns only newly materialized semantic records."],
        "prohibited_adoption_claims": ["No source component is itself a portfolio object."],
    }
    manifest["closure_hash"] = canonical_dossier_hash(manifest)
    return manifest


def _grant_preimage(grant: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in grant.items() if key != "grant_id"}


def create_scale01_root_grant(
    *,
    repository_root: Path,
    roots: Mapping[str, Path],
    output_path: Path,
    expires_at: datetime,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create one immutable capability-read-only grant for the exact real dossier roots."""

    repository_root = _resolve_repository_root(repository_root)
    contract, _contract_raw = _load_contract(repository_root)
    expected, registration_hashes, authority_hashes = _load_expected_set(repository_root, contract)
    registered_roots = _resolve_roots(roots, registration_hashes)
    output = _require_output_outside_roots(output_path, registered_roots, "root-grant output")
    current = now or datetime.now(UTC)
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise Gate6EligibilityError("root grant expiry must be timezone-aware")
    expiry = expires_at.astimezone(UTC)
    if expiry <= current.astimezone(UTC):
        raise Gate6EligibilityError("root grant expiry must be in the future")
    root_grant_contract = _require_mapping(contract.get("root_grant"), "root grant contract")
    _require_keys(
        root_grant_contract, {"schema_id", "schema_version", "enforcement", "allowed_operations"}, "root grant contract"
    )
    grant: dict[str, Any] = {
        "schema_id": root_grant_contract["schema_id"],
        "schema_version": root_grant_contract["schema_version"],
        "expected_set_ref": {
            "expected_set_id": expected.expected_set_id,
            "revision": expected.revision,
            "content_sha256": expected.content_hash,
            "dossier_id": expected.dossier_id,
            "package_id": expected.package_id,
            "package_version": expected.package_version,
            "manifest_sha256": expected.manifest_sha256,
        },
        "authority_refs": {
            "dossier_expected_set_file_sha256": authority_hashes["dossier"],
            "path_registration_file_sha256": authority_hashes["path"],
        },
        "enforcement": root_grant_contract["enforcement"],
        "allowed_operations": root_grant_contract["allowed_operations"],
        "expires_at": _canonical_timestamp(expiry),
        "roots": [
            {
                "root_id": root_id,
                "registration_hash": registration_hashes[root_id],
                "root_identity_hash": registered_roots[root_id].registration_hash,
                "member_set_sha256": _member_set_hash(expected, root_id),
            }
            for root_id in ("repo", "vault")
        ],
    }
    grant["grant_id"] = f"g6rg_{sha256_hex(canonical_bytes(_grant_preimage(grant)))}"
    validator = _schema_from_contract(repository_root, contract, "root_grant")
    _validate_schema(validator, grant, "Gate 6 read-only root grant")
    return _immutable_publish(output, grant, "Gate 6 read-only root grant")


def _load_root_grant(
    *,
    repository_root: Path,
    contract: Mapping[str, Any],
    expected: AcceptedExpectedSet,
    registration_hashes: Mapping[str, str],
    authority_hashes: Mapping[str, str],
    registered_roots: Mapping[str, RegisteredRoot],
    root_grant_path: Path,
    now: datetime,
) -> tuple[dict[str, Any], bytes]:
    try:
        grant_path = root_grant_path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise Gate6EligibilityError("root grant is unavailable") from exc
    grant, raw = _canonical_json(grant_path, "Gate 6 read-only root grant")
    validator = _schema_from_contract(repository_root, contract, "root_grant")
    _validate_schema(validator, grant, "Gate 6 read-only root grant")
    root_grant_contract = _require_mapping(contract.get("root_grant"), "root grant contract")
    if (
        grant.get("schema_id") != root_grant_contract.get("schema_id")
        or grant.get("schema_version") != root_grant_contract.get("schema_version")
        or grant.get("enforcement") != root_grant_contract.get("enforcement")
        or grant.get("allowed_operations") != root_grant_contract.get("allowed_operations")
        or grant.get("grant_id") != f"g6rg_{sha256_hex(canonical_bytes(_grant_preimage(grant)))}"
    ):
        raise Gate6EligibilityError("root grant identity or capability policy mismatch")
    expected_ref = {
        "expected_set_id": expected.expected_set_id,
        "revision": expected.revision,
        "content_sha256": expected.content_hash,
        "dossier_id": expected.dossier_id,
        "package_id": expected.package_id,
        "package_version": expected.package_version,
        "manifest_sha256": expected.manifest_sha256,
    }
    if grant.get("expected_set_ref") != expected_ref or grant.get("authority_refs") != {
        "dossier_expected_set_file_sha256": authority_hashes["dossier"],
        "path_registration_file_sha256": authority_hashes["path"],
    }:
        raise Gate6EligibilityError("root grant does not bind the accepted WP6.6 dossier")
    if parse_utc_timestamp(str(grant.get("expires_at"))) <= now.astimezone(UTC):
        raise Gate6EligibilityError("root grant is expired")
    grants = grant.get("roots")
    if not isinstance(grants, list) or len(grants) != 2:
        raise Gate6EligibilityError("root grant has an invalid root set")
    for root_id in ("repo", "vault"):
        row = next((row for row in grants if isinstance(row, Mapping) and row.get("root_id") == root_id), None)
        if not isinstance(row, Mapping) or row != {
            "root_id": root_id,
            "registration_hash": registration_hashes[root_id],
            "root_identity_hash": registered_roots[root_id].registration_hash,
            "member_set_sha256": _member_set_hash(expected, root_id),
        }:
            raise Gate6EligibilityError(f"root grant mismatch for {root_id}")
    return grant, raw


def certify_scale01_eligibility(
    *,
    repository_root: Path,
    roots: Mapping[str, Path],
    root_grant_path: Path,
    output_path: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Certify one eligible, provider-free SCALE-01 preflight envelope without writing the dossier."""

    repository_root = _resolve_repository_root(repository_root)
    contract, contract_raw = _load_contract(repository_root)
    expected, registration_hashes, authority_hashes = _load_expected_set(repository_root, contract)
    registered_roots = _resolve_roots(roots, registration_hashes)
    output = _require_output_outside_roots(output_path, registered_roots, "eligibility-envelope output")
    try:
        grant_path = root_grant_path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise Gate6EligibilityError("root grant is unavailable") from exc
    if output == grant_path:
        raise Gate6EligibilityError("eligibility-envelope output must not replace the root grant")
    current = now or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise Gate6EligibilityError("Gate 6 clock must be timezone-aware")
    grant, grant_raw = _load_root_grant(
        repository_root=repository_root,
        contract=contract,
        expected=expected,
        registration_hashes=registration_hashes,
        authority_hashes=authority_hashes,
        registered_roots=registered_roots,
        root_grant_path=grant_path,
        now=current,
    )
    read_only_capabilities = _issue_read_only_capabilities(grant, registered_roots)
    manifest = _candidate_manifest(expected)
    admission_contract = _require_mapping(contract.get("admission"), "admission contract")
    _require_keys(
        admission_contract,
        {"member_count", "event_count", "event_type", "provider_execution", "dispatchable"},
        "admission contract",
    )
    if canonical_dossier_hash(manifest) != expected.manifest_sha256:
        raise Gate6EligibilityError("fixed TDA-scale admission manifest no longer matches the accepted expected set")
    try:
        prepared = prepare_dossier_admission(
            expected_set=expected,
            current_expected_set_revision=expected.revision,
            candidate_members=expected.members,
            candidate_manifest=manifest,
            registered_roots={},
            read_only_capabilities=read_only_capabilities,
        )
    except DossierAdmissionRejected as exc:
        raise Gate6EligibilityError(f"real dossier admission failed closed: {exc}") from exc
    if (
        len(expected.members) != admission_contract.get("member_count")
        or len(prepared.events) != admission_contract.get("event_count")
        or not prepared.events
        or prepared.events[0].get("event_type") != admission_contract.get("event_type")
        or prepared.events[0].get("payload", {}).get("provider_execution")
        != admission_contract.get("provider_execution")
        or admission_contract.get("dispatchable") is not False
    ):
        raise Gate6EligibilityError("real dossier admission does not satisfy the fixed Gate 6 cardinality")
    verdict = _require_mapping(contract.get("verdict"), "eligibility verdict contract")
    _require_keys(
        verdict,
        {
            "schema_id",
            "schema_version",
            "eligibility_verdict",
            "dispatchable",
            "execution_authorized",
            "provider_execution",
        },
        "eligibility verdict contract",
    )
    envelope: dict[str, Any] = {
        "schema_id": verdict["schema_id"],
        "schema_version": verdict["schema_version"],
        "contract": {"repository_path": _CONTRACT_PATH.as_posix(), "raw_sha256": sha256_hex(contract_raw)},
        "expected_set": {
            "expected_set_id": expected.expected_set_id,
            "revision": expected.revision,
            "content_sha256": expected.content_hash,
            "dossier_id": expected.dossier_id,
            "package_id": expected.package_id,
            "package_version": expected.package_version,
            "manifest_sha256": expected.manifest_sha256,
        },
        "dossier_admission": {
            "event_type": prepared.events[0]["event_type"],
            "event_count": len(prepared.events),
            "member_count": len(prepared.observed_members),
            "member_closure_sha256": prepared.closure_hash,
            "provider_execution": admission_contract["provider_execution"],
            "write_mode": "none",
        },
        "root_grant": {
            "grant_id": grant["grant_id"],
            "raw_sha256": sha256_hex(grant_raw),
            "expires_at": grant["expires_at"],
        },
        "eligibility_verdict": verdict["eligibility_verdict"],
        "dispatchable": verdict["dispatchable"],
        "execution_authorized": verdict["execution_authorized"],
        "provider_execution": verdict["provider_execution"],
    }
    preimage = dict(envelope)
    envelope["envelope_id"] = f"g6env_{sha256_hex(canonical_bytes(preimage))}"
    validator = _schema_from_contract(repository_root, contract, "eligibility_envelope")
    _validate_schema(validator, envelope, "Gate 6 eligibility envelope")
    return _immutable_publish(output, envelope, "Gate 6 eligibility envelope")
