"""Read-only admission of the store-selected Gate 6 code subject.

The repository foundation supplies immutable store identity pins.  The control
store's append-only ``binding-repair-current.json`` selects the exact clean Git
subject that may interpret that store.  This module joins those two authorities
without loading the obsolete foundation code-root and schema-root snapshot.
"""

from __future__ import annotations

import json
import os
import stat
import tarfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system.git_execution import run_git
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.identity import (
    StoreOriginWitness,
    _validate_external_witness_for_store,
    load_restore_binding_transaction,
    load_store_manifest_unbound,
    load_store_origin_witness,
    validate_approved_origin_witness_path,
)
from research_system.store.layout import require_existing_control_root
from research_system.store.ledger import EventLedger
from research_system.store.receipts import validate_scoped_receipt_index


CURRENT_BINDING_RELATIVE_PATH = Path("manifests/binding-repair-current.json")
_BINDING_CONFIG_RELATIVE_PATH = Path("manifests/binding-repair-control-binding.json")
_ROUTE_RELATIVE_PATH = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
_SOURCE_RELATIVE_PATHS = (
    Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md"),
    Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md"),
)
_BINDING_BASE_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "project_id",
        "store_identity",
        "control_root",
        "code_roots",
        "schema_root",
        "origin_witness_sha256",
        "git_head",
        "git_tree",
        "git_clean",
        "schema_catalogue_sha256",
        "route",
        "sources",
        "stale_evidence",
        "command_payload_hash",
        "owner_actor_id",
        "owner_action",
        "idempotency_key",
        "prior_restore_transaction_id",
        "prior_restore_intended_manifest_sha256",
        "binding_config_path",
        "binding_config_sha256",
    }
)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _require_physical_path(path: Path, *, kind: str, label: str) -> Path:
    candidate = Path(os.path.abspath(os.fspath(path)))
    if not candidate.is_absolute() or not candidate.anchor:
        raise IntegrityError(f"{label} must be an absolute physical path")
    current = Path(candidate.anchor)
    parts = candidate.relative_to(current).parts
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for index, part in enumerate(parts):
        current /= part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise IntegrityError(f"{label} is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse:
            raise IntegrityError(f"{label} contains a redirected path component")
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise IntegrityError(f"{label} has a non-directory ancestor")
    try:
        resolved = candidate.resolve(strict=True)
        metadata = resolved.lstat()
    except OSError as exc:
        raise IntegrityError(f"{label} is unavailable") from exc
    if resolved != candidate:
        raise IntegrityError(f"{label} is redirected")
    if kind == "directory" and not stat.S_ISDIR(metadata.st_mode):
        raise IntegrityError(f"{label} is not a physical directory")
    if kind == "file" and not stat.S_ISREG(metadata.st_mode):
        raise IntegrityError(f"{label} is not a physical regular file")
    return resolved


def _read_canonical_json(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    physical = _require_physical_path(path, kind="file", label=label)
    try:
        raw = physical.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"{label} is invalid") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise IntegrityError(f"{label} is not canonical JSON")
    return value, raw


def _git(root: Path, *arguments: str, text: bool = True):
    result = run_git(
        root,
        *arguments,
        text=text,
        unavailable_message="current binding Git inspection is unavailable",
    )
    if result.returncode != 0:
        stderr = result.stderr if text else result.stderr.decode("utf-8", errors="replace")
        raise IntegrityError(f"current binding Git inspection failed: {str(stderr).strip()}")
    return result.stdout


def _committed_blob(root: Path, relative: Path, commit: str, *, label: str) -> bytes:
    listing = bytes(_git(root, "ls-tree", "-z", commit, "--", relative.as_posix(), text=False))
    entries = [entry for entry in listing.split(b"\0") if entry]
    expected_path = relative.as_posix().encode("utf-8")
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise IntegrityError(f"{label} is absent from the bound Git subject")
    header, listed_path = entries[0].split(b"\t", 1)
    fields = header.split(b" ")
    if len(fields) != 3 or fields[0] not in {b"100644", b"100755"} or fields[1] != b"blob":
        raise IntegrityError(f"{label} is not a committed regular file")
    if listed_path != expected_path:
        raise IntegrityError(f"{label} Git path differs from the requested path")
    object_id = fields[2].decode("ascii")
    return bytes(_git(root, "cat-file", "blob", object_id, text=False))


def _read_bound_file(root: Path, relative: Path, commit: str, *, label: str) -> bytes:
    expected = _committed_blob(root, relative, commit, label=label)
    path = _require_physical_path(root / relative, kind="file", label=label)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise IntegrityError(f"{label} is unavailable") from exc
    if raw != expected:
        raise IntegrityError(f"{label} differs from the bound Git subject")
    return raw


def _is_schema_registry_input(relative: Path) -> bool:
    if relative.name.endswith(".schema.json") or relative == Path("schema-identity-history.json"):
        return True
    if (
        relative.parent != Path("history")
        or not relative.name.startswith("sha256-")
        or not relative.name.endswith(".json")
    ):
        return False
    return _is_sha256(relative.name.removeprefix("sha256-").removesuffix(".json"))


def _schema_catalogue(root: Path, schema_root: Path, commit: str) -> str:
    archive = bytes(
        _git(
            root,
            "archive",
            "--format=tar",
            commit,
            "--",
            ".research-system/schemas",
            text=False,
        )
    )
    committed: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=BytesIO(archive), mode="r:") as bundle:
            for member in bundle.getmembers():
                path = Path(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise IntegrityError("current binding schema catalogue contains an invalid path")
                try:
                    relative_path = path.relative_to(Path(".research-system/schemas"))
                except ValueError:
                    continue
                if relative_path == Path("."):
                    continue
                relative = relative_path.as_posix()
                if not _is_schema_registry_input(Path(relative)):
                    continue
                if not member.isfile():
                    raise IntegrityError("current binding schema catalogue contains a non-regular path")
                handle = bundle.extractfile(member)
                if relative in committed or handle is None:
                    raise IntegrityError("current binding schema catalogue is ambiguous")
                committed[relative] = handle.read()
    except (tarfile.TarError, OSError, ValueError) as exc:
        raise IntegrityError("current binding Git schema catalogue is invalid") from exc
    physical_root = _require_physical_path(schema_root, kind="directory", label="current binding schema root")
    physical_paths = sorted(
        (path for path in physical_root.rglob("*") if _is_schema_registry_input(path.relative_to(physical_root))),
        key=lambda value: value.as_posix(),
    )
    relatives = {path.relative_to(physical_root).as_posix() for path in physical_paths}
    if not committed or relatives != set(committed):
        raise IntegrityError("current binding schema catalogue differs from the bound Git subject")
    records: list[dict[str, str]] = []
    for path in physical_paths:
        relative = path.relative_to(physical_root).as_posix()
        physical = _require_physical_path(path, kind="file", label="current binding schema file")
        raw = physical.read_bytes()
        if raw != committed[relative]:
            raise IntegrityError("current binding schema file differs from the bound Git subject")
        records.append({"path": relative, "sha256": sha256_hex(raw)})
    return sha256_hex(canonical_bytes(records))


def _load_foundation(path: Path) -> tuple[dict[str, Any], StoreOriginWitness, Path]:
    physical = _require_physical_path(path, kind="file", label="current binding foundation")
    try:
        value = yaml.safe_load(physical.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError("current binding foundation is unavailable") from exc
    if not isinstance(value, dict):
        raise ConfigurationError("current binding foundation must be an object")
    expected_hash = sha256_hex(
        canonical_bytes({key: item for key, item in value.items() if key != "foundation_sha256"})
    )
    if value.get("foundation_sha256") != expected_hash:
        raise ConfigurationError("current binding foundation hash mismatch")
    try:
        project_id = validate_id(str(value.get("project_id")), "project")
    except ValueError as exc:
        raise ConfigurationError("current binding foundation project identity is invalid") from exc
    if not _is_sha256(value.get("store_identity")) or not _is_sha256(value.get("origin_witness_sha256")):
        raise ConfigurationError("current binding foundation digest is invalid")
    control_value = value.get("control_root")
    witness_value = value.get("origin_witness_path")
    origin_value = value.get("origin_authority_root")
    if not all(
        isinstance(item, str) and Path(item).is_absolute() for item in (control_value, witness_value, origin_value)
    ):
        raise ConfigurationError("current binding foundation path is invalid")
    witness = load_store_origin_witness(
        Path(witness_value),
        expected_sha256=str(value["origin_witness_sha256"]),
    )
    witness_path, origin_root = validate_approved_origin_witness_path(Path(witness_value), witness)
    if (
        witness.project_id != project_id
        or witness.store_identity != value["store_identity"]
        or origin_root != Path(origin_value).resolve(strict=True)
    ):
        raise ConfigurationError("current binding foundation differs from its origin witness")
    return value, witness, witness_path


def _validate_binding_shape(value: dict[str, Any]) -> None:
    version = value.get("schema_version")
    expected_fields = set(_BINDING_BASE_FIELDS)
    if version == "1.1.0":
        expected_fields.add("predecessor_binding_sha256")
        if value.get("owner_action") == "advance-reviewed-route-successor-store-binding":
            expected_fields.add("route_successor_authority")
        elif value.get("owner_action") != "advance-clean-descendant-store-binding":
            raise IntegrityError("current binding owner action is invalid")
    elif version == "1.0.0":
        if value.get("owner_action") != "repair-stale-store-binding":
            raise IntegrityError("current binding owner action is invalid")
    else:
        raise IntegrityError("current binding schema version is unsupported")
    if set(value) != expected_fields:
        raise IntegrityError("current binding fields are not exact")
    if value.get("schema_id") != "ars://internal/store-binding-recovery":
        raise IntegrityError("current binding schema identity is invalid")


def _binding_git_tree(repository_root: Path, binding: dict[str, Any]) -> str:
    head = binding.get("git_head")
    expected_tree = binding.get("git_tree")
    if not (
        isinstance(head, str)
        and len(head) == 40
        and all(character in "0123456789abcdef" for character in head)
        and isinstance(expected_tree, str)
        and len(expected_tree) == 40
        and all(character in "0123456789abcdef" for character in expected_tree)
    ):
        raise IntegrityError("current binding transition Git identity is invalid")
    commit = str(_git(repository_root, "rev-parse", "--verify", f"{head}^{{commit}}")).strip()
    tree = str(_git(repository_root, "rev-parse", "--verify", f"{head}^{{tree}}")).strip()
    if commit != head or tree != expected_tree:
        raise IntegrityError("current binding transition Git subject is invalid")
    return head


def _validate_binding_transition(
    repository_root: Path,
    child: dict[str, Any],
    predecessor: dict[str, Any],
    predecessor_sha256: str,
) -> None:
    """Validate the authority mode joining one immutable binding-chain link."""

    stable_fields = (
        "project_id",
        "store_identity",
        "control_root",
        "code_roots",
        "schema_root",
        "origin_witness_sha256",
        "sources",
        "prior_restore_transaction_id",
        "prior_restore_intended_manifest_sha256",
        "binding_config_path",
        "binding_config_sha256",
    )
    if any(predecessor.get(field) != child.get(field) for field in stable_fields):
        raise IntegrityError("current binding predecessor identity mismatch")
    predecessor_head = _binding_git_tree(repository_root, predecessor)
    child_head = _binding_git_tree(repository_root, child)
    owner_action = child.get("owner_action")
    if owner_action == "advance-clean-descendant-store-binding":
        if any(predecessor.get(field) != child.get(field) for field in ("schema_catalogue_sha256", "route", "sources")):
            raise IntegrityError("clean descendant current binding changed governed evidence")
        relation = run_git(
            repository_root,
            "merge-base",
            "--is-ancestor",
            predecessor_head,
            child_head,
            unavailable_message="current binding Git ancestry inspection is unavailable",
        )
        if relation.returncode != 0:
            if relation.returncode == 1:
                raise IntegrityError("current binding subject is not a clean Git descendant")
            raise IntegrityError("current binding Git ancestry inspection failed")
        return
    if owner_action == "advance-reviewed-route-successor-store-binding":
        predecessor_route = predecessor.get("route")
        successor_route = child.get("route")
        expected_authority = {
            "predecessor_binding_sha256": predecessor_sha256,
            "candidate_git_head": child_head,
            "predecessor_route_sha256": (
                predecessor_route.get("sha256") if isinstance(predecessor_route, dict) else None
            ),
            "successor_route_sha256": successor_route.get("sha256") if isinstance(successor_route, dict) else None,
        }
        if child.get("route_successor_authority") != expected_authority:
            raise IntegrityError("current binding reviewed route successor authority is invalid")
        if predecessor.get("schema_version") != "1.0.0":
            raise IntegrityError("current binding reviewed route successor requires the legacy repair root")
        return
    raise IntegrityError("current binding owner action is invalid")


def _validate_binding_chain(
    repository_root: Path,
    control_root: Path,
    schemas: SchemaRegistry,
    current: dict[str, Any],
    current_sha256: str,
) -> None:
    seen = {current_sha256}
    child = current
    while child.get("schema_version") == "1.1.0":
        predecessor_sha256 = child.get("predecessor_binding_sha256")
        if not _is_sha256(predecessor_sha256) or predecessor_sha256 in seen:
            raise IntegrityError("current binding predecessor chain is invalid")
        predecessor_path = control_root / "objects" / "binding-repair" / f"sha256-{predecessor_sha256}.json"
        predecessor, predecessor_raw = _read_canonical_json(
            predecessor_path,
            label="current binding predecessor object",
        )
        if sha256_hex(predecessor_raw) != predecessor_sha256:
            raise IntegrityError("current binding predecessor object hash mismatch")
        _validate_binding_shape(predecessor)
        predecessor_schema_id = (
            "ars://wp6-6/gate6/binding-repair/object/StoreBindingAdvance"
            if predecessor["schema_version"] == "1.1.0"
            else "ars://wp6-6/gate6/binding-repair/object/StoreBindingRepair"
        )
        try:
            schemas.validate(predecessor_schema_id, predecessor)
        except SchemaError as exc:
            raise IntegrityError("current binding predecessor object schema is invalid") from exc
        _validate_binding_transition(repository_root, child, predecessor, predecessor_sha256)
        seen.add(predecessor_sha256)
        child = predecessor
    if child.get("schema_version") != "1.0.0":
        raise IntegrityError("current binding predecessor chain has no repair root")


def _validate_hash_chain(events: tuple[dict[str, Any], ...]) -> None:
    position = 0
    previous_hash = "0" * 64
    for event in events:
        if event.get("global_position") != position + 1 or event.get("previous_event_hash") != previous_hash:
            raise IntegrityError("current binding ledger chain mismatch")
        unsigned = dict(event)
        recorded = unsigned.pop("event_hash", None)
        if recorded != sha256_hex(canonical_bytes(unsigned)):
            raise IntegrityError("current binding ledger event hash mismatch")
        position += 1
        previous_hash = str(recorded)


def _validate_binding_event_lineage(binding_events: list[dict[str, Any]]) -> None:
    previous_binding_sha256: str | None = None
    for event in binding_events:
        payload = event.get("payload")
        if not isinstance(payload, dict) or not _is_sha256(payload.get("recovery_binding_sha256")):
            raise IntegrityError("current binding event lineage is invalid")
        recovery_binding_sha256 = payload["recovery_binding_sha256"]
        if event.get("event_type") == "StoreBindingRepaired" and previous_binding_sha256 is not None:
            raise IntegrityError("current binding event lineage is invalid")
        if (
            event.get("event_type") == "StoreBindingAdvanced"
            and previous_binding_sha256 is not None
            and payload.get("predecessor_binding_sha256") != previous_binding_sha256
        ):
            raise IntegrityError("current binding event lineage is invalid")
        previous_binding_sha256 = recovery_binding_sha256


def _validate_receipt_and_event(
    *,
    control_root: Path,
    project_id: str,
    store_identity: str,
    schemas: SchemaRegistry,
    binding: dict[str, Any],
    binding_raw: bytes,
) -> None:
    advanced = binding["schema_version"] == "1.1.0"
    binding_sha256 = sha256_hex(binding_raw)
    payload_hash = str(binding["command_payload_hash"])
    command_id = f"{'binding-advance' if advanced else 'binding-repair'}-{payload_hash}"
    receipt, receipt_raw = _read_canonical_json(
        control_root / "receipts" / f"{command_id}.json",
        label="current binding receipt",
    )
    receipt_schema_id = (
        "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingAdvance"
        if advanced
        else "ars://wp6-6/gate6/binding-repair/receipt/StoreBindingRepair"
    )
    try:
        schemas.validate(receipt_schema_id, receipt)
    except SchemaError as exc:
        raise IntegrityError("current binding receipt schema is invalid") from exc
    _require_physical_path(
        control_root / "events" / project_id,
        kind="directory",
        label="current binding project event directory",
    )
    ledger = EventLedger(control_root, project_id, schemas, store_identity=store_identity)
    events = tuple(ledger.iter_events())
    _validate_hash_chain(events)
    outcome = receipt.get("outcome")
    event_batch_id = outcome.get("event_batch_id") if isinstance(outcome, dict) else None
    event_type = "StoreBindingAdvanced" if advanced else "StoreBindingRepaired"
    command_type = "AdvanceStoreBinding" if advanced else "RepairStoreBinding"
    matches = [
        event
        for event in events
        if event.get("transaction_id") == event_batch_id
        and event.get("event_type") == event_type
        and event.get("command_type") == command_type
        and event.get("command_payload_hash") == payload_hash
    ]
    binding_events = [
        event for event in events if event.get("event_type") in {"StoreBindingRepaired", "StoreBindingAdvanced"}
    ]
    _validate_binding_event_lineage(binding_events)
    if len(matches) != 1 or not binding_events or matches[0] is not binding_events[-1]:
        raise IntegrityError("current binding event is missing, ambiguous, or stale")
    event = matches[0]
    expected_event_provenance = {
        "command_id": command_id,
        "project_id": project_id,
        "stream_id": project_id,
        "actor_id": binding.get("owner_actor_id"),
        "idempotency_key": binding.get("idempotency_key"),
        "authority_grant_id": "store-binding-recovery",
        "correlation_id": binding.get("idempotency_key"),
        "causation_id": None,
        "transaction_index": 1,
        "transaction_count": 1,
    }
    if any(event.get(field) != expected for field, expected in expected_event_provenance.items()):
        raise IntegrityError("current binding event provenance is invalid")
    try:
        command_binding = schemas.command_binding(command_type)
        if command_binding is None or event.get("command_schema_id") != command_binding.schema_id:
            raise SchemaError("binding event command schema family mismatch")
        schemas.resolve_identity(
            str(event.get("command_schema_id")),
            str(event.get("command_schema_version")),
            expected_sha256=str(event.get("command_schema_sha256")),
        )
        schemas.validate(str(event.get("schema_id")), event, schema_version=str(event.get("schema_version")))
    except SchemaError as exc:
        raise IntegrityError("current binding event schema provenance is invalid") from exc
    payload = event.get("payload")
    if advanced:
        expected_relation = isinstance(payload, dict) and (
            payload.get("predecessor_binding_sha256") == binding.get("predecessor_binding_sha256")
        )
    else:
        expected_relation = isinstance(payload, dict) and (
            payload.get("prior_manifest_sha256") == binding.get("prior_restore_intended_manifest_sha256")
        )
    object_path = control_root / "objects" / "binding-repair" / f"sha256-{binding_sha256}.json"
    if (
        not isinstance(payload, dict)
        or payload.get("recovery_binding_sha256") != binding_sha256
        or payload.get("recovery_binding_path") != CURRENT_BINDING_RELATIVE_PATH.as_posix()
        or payload.get("object_path") != object_path.relative_to(control_root).as_posix()
        or payload.get("git_head") != binding.get("git_head")
        or payload.get("git_tree") != binding.get("git_tree")
        or not expected_relation
    ):
        raise IntegrityError("current binding event/object relation is invalid")
    if (
        receipt_raw != canonical_bytes(receipt)
        or receipt.get("command_id") != command_id
        or receipt.get("status") != "accepted"
        or receipt.get("payload_hash") != payload_hash
        or not isinstance(outcome, dict)
        or outcome.get("event_batch_id") != event.get("transaction_id")
        or outcome.get("observed_stream_version") != event.get("stream_version")
    ):
        raise IntegrityError("current binding receipt/event relation is invalid")
    scope = [binding.get("owner_actor_id"), "store-binding-recovery", command_type, binding.get("idempotency_key")]
    index, _ = _read_canonical_json(
        control_root / "receipts" / "idempotency" / f"{sha256_hex(canonical_bytes(scope))}.json",
        label="current binding scoped receipt",
    )
    expected_authority = sha256_hex(
        canonical_bytes({"actor_id": binding.get("owner_actor_id"), "action": binding.get("owner_action")})
    )
    if type(event.get("stream_version")) is not int:
        raise IntegrityError("current binding scoped receipt is invalid")
    try:
        validate_scoped_receipt_index(
            index,
            tuple(scope),
            payload_hash,
            expected_authority,
            event["stream_version"] - 1,
            project_id=project_id,
            target_stream_id=project_id,
        )
    except (ConflictError, ValueError) as exc:
        raise IntegrityError("current binding scoped receipt is invalid") from exc
    if index.get("receipt") != receipt:
        raise IntegrityError("current binding scoped receipt is invalid")


@dataclass(frozen=True, slots=True)
class VerifiedCurrentBinding:
    """One exact, read-only store/code admission result."""

    control_root: Path
    project_id: str
    store_identity: str
    repository_root: Path
    schema_root: Path
    origin_witness: StoreOriginWitness
    origin_witness_path: Path
    binding_sha256: str
    _binding_raw: bytes
    _manifest_raw: bytes
    foundation_path: Path

    @property
    def binding(self) -> dict[str, Any]:
        """Return an isolated copy of the admitted immutable binding."""

        return json.loads(self._binding_raw)

    @property
    def manifest(self) -> dict[str, Any]:
        """Return an isolated copy of the admitted immutable manifest."""

        return json.loads(self._manifest_raw)

    def revalidate(self) -> "VerifiedCurrentBinding":
        """Re-read the admission and reject any changed current-binding generation."""

        return load_current_binding(
            foundation_path=self.foundation_path,
            repository_root=self.repository_root,
            expected_control_root=self.control_root,
            expected_project_id=self.project_id,
            expected_store_identity=self.store_identity,
            expected_binding_sha256=self.binding_sha256,
        )


def load_current_binding(
    *,
    foundation_path: Path,
    repository_root: Path,
    expected_control_root: Path,
    expected_project_id: str,
    expected_store_identity: str,
    expected_binding_sha256: str | None = None,
) -> VerifiedCurrentBinding:
    """Join foundation pins, the live store and its exact current code subject."""

    foundation, witness, witness_path = _load_foundation(foundation_path)
    repository = _require_physical_path(repository_root, kind="directory", label="current binding repository root")
    control = _require_physical_path(expected_control_root, kind="directory", label="current binding control root")
    project_id = validate_id(expected_project_id, "project")
    if not _is_sha256(expected_store_identity):
        raise ConfigurationError("SPEC operator store identity is invalid")
    try:
        foundation_control = Path(str(foundation.get("control_root"))).resolve(strict=True)
    except OSError as exc:
        raise ConfigurationError("SPEC operator identity differs from the repository foundation") from exc
    if (
        foundation.get("project_id") != project_id
        or foundation.get("store_identity") != expected_store_identity
        or foundation_control != control
    ):
        raise ConfigurationError("SPEC operator identity differs from the repository foundation")
    require_existing_control_root([repository], control)

    pointer_path = control / CURRENT_BINDING_RELATIVE_PATH
    binding, binding_raw = _read_canonical_json(pointer_path, label="current store binding")
    binding_sha256 = sha256_hex(binding_raw)
    if expected_binding_sha256 is not None and binding_sha256 != expected_binding_sha256:
        raise ConflictError("current store binding changed during the operation")
    _validate_binding_shape(binding)
    schema_root = repository / ".research-system" / "schemas"
    if (
        binding.get("project_id") != project_id
        or binding.get("store_identity") != expected_store_identity
        or binding.get("control_root") != str(control)
        or binding.get("origin_witness_sha256") != witness.raw_sha256
        or binding.get("code_roots") != [str(repository)]
        or binding.get("schema_root") != str(schema_root)
        or binding.get("git_clean") is not True
    ):
        raise IntegrityError("current store binding identity is invalid")
    head = str(_git(repository, "rev-parse", "HEAD")).strip()
    tree = str(_git(repository, "rev-parse", "HEAD^{tree}")).strip()
    if head != binding.get("git_head") or tree != binding.get("git_tree"):
        raise IntegrityError("current store binding Git subject changed")
    if str(_git(repository, "status", "--porcelain=v1", "--untracked-files=all")).strip():
        raise IntegrityError("current store binding repository is dirty")
    catalogue_sha256 = _schema_catalogue(repository, schema_root, head)
    if catalogue_sha256 != binding.get("schema_catalogue_sha256"):
        raise IntegrityError("current store binding schema catalogue changed")
    route = binding.get("route")
    sources = binding.get("sources")
    if (
        not isinstance(route, dict)
        or set(route) != {"ref", "sha256"}
        or route.get("ref") != _ROUTE_RELATIVE_PATH.as_posix()
        or not _is_sha256(route.get("sha256"))
        or not isinstance(sources, list)
        or len(sources) != 2
    ):
        raise IntegrityError("current store binding source evidence is invalid")
    route_raw = _read_bound_file(repository, _ROUTE_RELATIVE_PATH, head, label="bound SPEC route package")
    if sha256_hex(route_raw) != route["sha256"]:
        raise IntegrityError("bound SPEC route package hash mismatch")
    for expected_path, source in zip(_SOURCE_RELATIVE_PATHS, sources, strict=True):
        if (
            not isinstance(source, dict)
            or set(source) != {"ref", "sha256", "size_bytes"}
            or source.get("ref") != expected_path.as_posix()
            or not _is_sha256(source.get("sha256"))
            or type(source.get("size_bytes")) is not int
            or source["size_bytes"] < 1
        ):
            raise IntegrityError("current store binding SPEC source evidence is invalid")
        raw = _read_bound_file(repository, expected_path, head, label="bound SPEC source")
        if len(raw) != source["size_bytes"] or sha256_hex(raw) != source["sha256"]:
            raise IntegrityError("bound SPEC source bytes changed")

    schemas = runtime_schema_registry(schema_root, generation=f"{head}:{catalogue_sha256}")
    object_schema_id = (
        "ars://wp6-6/gate6/binding-repair/object/StoreBindingAdvance"
        if binding["schema_version"] == "1.1.0"
        else "ars://wp6-6/gate6/binding-repair/object/StoreBindingRepair"
    )
    try:
        schemas.validate(object_schema_id, binding)
    except SchemaError as exc:
        raise IntegrityError("current store binding object schema is invalid") from exc
    object_path = control / "objects" / "binding-repair" / f"sha256-{binding_sha256}.json"
    _object, object_raw = _read_canonical_json(object_path, label="current binding immutable object")
    if object_raw != binding_raw:
        raise IntegrityError("current binding immutable object differs from the selected pointer")
    _validate_binding_chain(repository, control, schemas, binding, binding_sha256)

    expected_binding_config = canonical_bytes(
        {
            "code_roots": binding["code_roots"],
            "control_root": binding["control_root"],
            "project_id": binding["project_id"],
            "schema_root": binding["schema_root"],
            "store_identity": binding["store_identity"],
        }
    )
    _binding_config, binding_config_raw = _read_canonical_json(
        control / _BINDING_CONFIG_RELATIVE_PATH,
        label="current binding control config",
    )
    if (
        binding.get("binding_config_path") != _BINDING_CONFIG_RELATIVE_PATH.as_posix()
        or binding.get("binding_config_sha256") != sha256_hex(expected_binding_config)
        or binding_config_raw != expected_binding_config
    ):
        raise IntegrityError("current binding control config is invalid")

    restore = load_restore_binding_transaction(control)
    if (
        not isinstance(restore, dict)
        or restore.get("transaction_id") != binding.get("prior_restore_transaction_id")
        or restore.get("intended_manifest_sha256") != binding.get("prior_restore_intended_manifest_sha256")
    ):
        raise IntegrityError("current binding restore predecessor is invalid")
    manifest = load_store_manifest_unbound(control)
    _validate_external_witness_for_store(control, manifest, witness)
    if (
        manifest.get("project_id") != project_id
        or manifest.get("store_identity") != expected_store_identity
        or manifest.get("control_root") != str(control)
        or manifest.get("code_roots") != binding["code_roots"]
        or manifest.get("schema_root") != binding["schema_root"]
        or manifest.get("origin_witness_path") != str(witness_path)
        or manifest.get("origin_witness_sha256") != witness.raw_sha256
    ):
        raise IntegrityError("current binding differs from the materialized store manifest")
    _validate_receipt_and_event(
        control_root=control,
        project_id=project_id,
        store_identity=expected_store_identity,
        schemas=schemas,
        binding=binding,
        binding_raw=binding_raw,
    )
    if _read_canonical_json(pointer_path, label="current store binding")[1] != binding_raw:
        raise ConflictError("current store binding changed during admission")
    final_head = str(_git(repository, "rev-parse", "HEAD")).strip()
    final_tree = str(_git(repository, "rev-parse", "HEAD^{tree}")).strip()
    if final_head != head or final_tree != tree:
        raise IntegrityError("current store binding Git subject changed during admission")
    if str(_git(repository, "status", "--porcelain=v1", "--untracked-files=all")).strip():
        raise IntegrityError("current store binding repository changed during admission")
    return VerifiedCurrentBinding(
        control_root=control,
        project_id=project_id,
        store_identity=expected_store_identity,
        repository_root=repository,
        schema_root=schema_root,
        origin_witness=witness,
        origin_witness_path=witness_path,
        binding_sha256=binding_sha256,
        _binding_raw=binding_raw,
        _manifest_raw=canonical_bytes(manifest),
        foundation_path=_require_physical_path(
            foundation_path,
            kind="file",
            label="current binding foundation",
        ),
    )


__all__ = ["CURRENT_BINDING_RELATIVE_PATH", "VerifiedCurrentBinding", "load_current_binding"]
