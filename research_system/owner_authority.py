"""Owner-operated publication and activation of SPEC-route authority grants."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess  # nosec B404 - fixed-argv, read-only Git identity checks
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError, ValidationError

from research_system.authority import (
    AuthorityGrant,
    OWNER_AUTHORITY_DECISION_SCHEMA_ID,
    OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
    SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
    SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
    _SCOPED_COMMAND_SUBJECT_KINDS,
    LedgerAuthorityGrantResolver,
    OwnerAuthorityAdministrationDecision,
    ScopedAuthorityGrant,
    is_scoped_authority_grant_schema,
    validate_scoped_grant_activation,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConfigurationError, IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.ids import validate_id
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


_ROUTE_RELATIVE = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
_ROUTE_SCHEMA_RELATIVE = Path(".research-system/schemas/contracts/wp6-6/spec-gate6-route.schema.json")
_CATALOGUE_RELATIVE = Path(".research-system/evals/expected/w11-portfolio-discovery-v1.json")
_CONFIG_FIELDS = frozenset({"authority_binding", "repository_root"})
_PUBLISH_FIELDS = frozenset(
    {
        "retry_key",
        "target_actor_id",
        "target_actor_class",
        "authority_lane",
        "actor_role",
        "subject_scope",
        "evidence_refs",
        "effective_at",
        "expires_at",
        "reason",
        "owner_action",
    }
)
_ACTIVATE_FIELDS = frozenset({"retry_key", "publication_command_id", "reason", "evidence_refs"})

# Disjoint role/stage lanes distilled from the accepted route rows and their
# catalogue eligible-profile semantics.  Shared command names are assigned to
# the narrow operation lane, never duplicated across caller-selectable roles.
_LANE_COMMAND_POLICY = {
    "operator/genesis": frozenset({"ImportAcceptedW11CatalogueGenesis"}),
    "research_designer/authority": frozenset({"RegisterAssayRubricContent", "RegisterAssayEvidenceScopeContent"}),
    "independent_reviewer/authority_observation": frozenset({"ObserveW11AuthorityFile", "RecordW11AuthorityReview"}),
    "authority_requester/authority": frozenset({"RequestW11AuthorityReview"}),
    "authority_proposer/authority": frozenset({"ProposeW11AuthorityDecision"}),
    "owner_decider/decision": frozenset({"ResolveDecision"}),
    "portfolio_steward/dossier_authority": frozenset({"RegisterDossierExpectedSetContent"}),
    "operator/path_authority": frozenset({"RegisterPathRegistrationContent"}),
    "operator/admission": frozenset({"AdmitResearchDossier"}),
    "scout/source_observation": frozenset({"IngestScoutObservationBatch"}),
    "portfolio_steward/spec_01_assay": frozenset({"RequestAssay"}),
    "producer/spec_01_assay": frozenset({"RecordAssayScore", "RecordAssayPartial"}),
    "producer/spec_brief_registration": frozenset({"RegisterArtefact"}),
    "independent_reviewer/spec_brief_review": frozenset({"RecordScientificReview"}),
    "owner_decider/spec_brief_use": frozenset({"SetArtefactUseAuthority"}),
    "operator/spec_01_context": frozenset(
        {
            "RequestContextPacket",
            "BeginContextCompilation",
            "CompleteContextCompilation",
            "PrepareOwnerOperatedContextHandoff",
            "ValidateOwnerOperatedContextHandoff",
            "IssueOwnerOperatedContextHandoff",
            "RecordOwnerOperatedContextDelivery",
        }
    ),
    "operator/spec_02_execution": frozenset(
        {
            "CreateTask",
            "RequestReadiness",
            "ApproveReadiness",
            "IssueDispatch",
            "RecordDispatchDelivery",
            "AcknowledgeDispatch",
            "ClaimDispatch",
            "RequestResourceGrant",
            "ClaimExecutionLease",
            "CreateAttempt",
            "ClaimAttempt",
            "StartAttempt",
            "CompleteAttempt",
            "ReleaseExecutionLease",
            "ReleaseResources",
        }
    ),
    "review_requester/outcome_review": frozenset({"RequestDiscoveryOutcomeReview"}),
    "independent_reviewer/outcome_review": frozenset({"ReviewDiscoveryOutcome"}),
    "portfolio_steward/promotion": frozenset({"ProposePromotionDecision"}),
    "portfolio_steward/spec_02_spike": frozenset({"RegisterSpikePlan", "ProposeSpikeExecutionDecision"}),
    "operator/spec_02_spike": frozenset({"StartSpike"}),
    "producer/spec_02_spike": frozenset({"RecordSpikeVerdict"}),
}
_LANE_CONTEXT_POLICY = {
    "operator/genesis": ({"genesis"}, {"Operator/auditor holding the exact independently verified bootstrap grant"}),
    "research_designer/authority": ({"authority"}, {"Research Designer"}),
    "independent_reviewer/authority_observation": ({"authority"}, {"independent verifier"}),
    "authority_requester/authority": ({"authority"}, {"Portfolio Steward", "Operator/auditor"}),
    "authority_proposer/authority": ({"authority"}, {"Portfolio Steward", "Gate 6 Manager"}),
    "owner_decider/decision": (
        {"authority", "promotion_stop", "spec_02_spike", "result_stop"},
        {"Stephen"},
    ),
    "portfolio_steward/dossier_authority": ({"authority"}, {"Portfolio Steward"}),
    "operator/path_authority": ({"authority"}, {"Operator/auditor"}),
    "operator/admission": ({"admission"}, {"Operator/auditor R2"}),
    "scout/source_observation": ({"source_observation"}, {"Scout"}),
    "portfolio_steward/spec_01_assay": ({"spec_01_assay"}, {"Portfolio Steward"}),
    "producer/spec_01_assay": ({"spec_01_assay"}, {"Assay producer"}),
    "producer/spec_brief_registration": ({"spec_01_brief"}, {"SPEC brief producer"}),
    "independent_reviewer/spec_brief_review": ({"spec_01_brief"}, {"independent verifier"}),
    "owner_decider/spec_brief_use": ({"spec_01_brief"}, {"Stephen"}),
    "operator/spec_01_context": ({"spec_01_brief"}, {"Operator/auditor"}),
    "operator/spec_02_execution": ({"spec_02_spike"}, {"Operator/auditor"}),
    "review_requester/outcome_review": (
        {"spec_01_outcome_review", "spec_02_outcome_review"},
        {"Portfolio Steward"},
    ),
    "independent_reviewer/outcome_review": (
        {"spec_01_outcome_review", "spec_02_outcome_review"},
        {"independent verifier"},
    ),
    "portfolio_steward/promotion": ({"promotion_stop", "result_stop"}, {"Portfolio Steward"}),
    "portfolio_steward/spec_02_spike": ({"spec_02_spike"}, {"Portfolio Steward"}),
    "operator/spec_02_spike": ({"spec_02_spike"}, {"Operator/auditor"}),
    "producer/spec_02_spike": ({"spec_02_spike"}, {"Spike producer"}),
}
_SPEC_FLOW_SUPPORT_LANES = frozenset(
    {
        "producer/spec_brief_registration",
        "independent_reviewer/spec_brief_review",
        "owner_decider/spec_brief_use",
        "operator/spec_01_context",
        "operator/spec_02_execution",
    }
)
_LANE_RISK_POLICY = {lane: ("R3" if lane in _SPEC_FLOW_SUPPORT_LANES else "R2") for lane in _LANE_COMMAND_POLICY}
_LANE_ALLOWED_ACTOR_CLASSES = {
    lane: (
        frozenset({"human"})
        if lane.startswith("owner_decider/")
        else frozenset({"agent", "service"})
        if lane.startswith("producer/")
        else frozenset({"human", "agent"})
        if lane.startswith("independent_reviewer/")
        else frozenset({"agent"})
        if lane.startswith("scout/")
        else frozenset({"human", "service"})
        if lane.startswith("operator/")
        else frozenset({"human", "agent", "service"})
    )
    for lane in _LANE_COMMAND_POLICY
}
_COMMAND_LANE = {command: lane for lane, commands in _LANE_COMMAND_POLICY.items() for command in commands}
_INACTIVE_GRANT_ERRORS = frozenset(
    {
        "authority grant revoked",
        "authority grant is not active",
        "authority grant not effective",
        "authority grant expired",
    }
)


def _read_canonical_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"invalid {label}") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise ConfigurationError(f"{label} must be one canonical JSON object")
    return value


def read_owner_authority_input(path: Path, *, operation: str) -> dict[str, Any]:
    """Read one strict canonical setup request without supplying defaults."""

    value = _read_canonical_object(Path(path).resolve(strict=True), label=f"authority {operation} input")
    expected = _PUBLISH_FIELDS if operation == "publish" else _ACTIVATE_FIELDS
    if set(value) != expected:
        raise ConfigurationError(f"authority {operation} input fields must be exact")
    return value


def _physical_directory(path: Path, *, label: str) -> Path:
    candidate = Path(os.path.abspath(os.fspath(path)))
    if not candidate.is_absolute() or not candidate.anchor:
        raise ConfigurationError(f"{label} must be absolute")
    current = Path(candidate.anchor)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in candidate.relative_to(current).parts:
        current /= part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise ConfigurationError(f"{label} physical path is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse:
            raise ConfigurationError(f"{label} physical path has a reparse component")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ConfigurationError(f"{label} physical path is not a directory")
    return candidate.resolve(strict=True)


def _require_authority_layout(root: Path, project_id: str) -> None:
    for relative in (
        Path("objects"),
        Path("objects/assurance_record"),
        Path("objects/authority_grant"),
        Path("events"),
        Path("events") / project_id,
        Path("manifests"),
        Path("receipts"),
        Path("receipts/idempotency"),
        Path("runtime"),
    ):
        resolved = _physical_directory(root / relative, label=f"authority store {relative.as_posix()}")
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ConfigurationError("authority store path escapes configured root") from exc


def _require_bounded_target(root: Path, relative: Path, *, label: str) -> None:
    """Reject existing redirected components while allowing a missing create suffix."""

    current = root
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise ConfigurationError(f"{label} physical path is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse:
            raise ConfigurationError(f"{label} physical path has a reparse component")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ConfigurationError(f"{label} physical ancestor is not a directory")


def _require_bounded_object_revision(
    root: Path,
    kind: str,
    object_id: str,
    revision: int,
    *,
    label: str,
) -> None:
    """Reject a redirected object directory or immutable revision file."""

    relative = Path("objects") / kind / object_id
    _require_bounded_target(root, relative, label=label)
    directory = root / relative
    if not directory.exists():
        return
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    try:
        matches = tuple(directory.glob(f"{revision:08d}-*.json"))
    except OSError as exc:
        raise ConfigurationError(f"{label} physical path is unavailable") from exc
    for candidate in matches:
        try:
            metadata = candidate.lstat()
        except OSError as exc:
            raise ConfigurationError(f"{label} revision path is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse:
            raise ConfigurationError(f"{label} revision path has a reparse component")
        if not stat.S_ISREG(metadata.st_mode):
            raise ConfigurationError(f"{label} revision path is not a regular file")
        try:
            candidate.resolve(strict=True).relative_to(root)
        except (OSError, ValueError) as exc:
            raise ConfigurationError(f"{label} revision path escapes configured root") from exc


def _lane_family(lane: str) -> str:
    if lane.startswith("owner_decider/"):
        return "owner"
    if lane.startswith("producer/"):
        return "producer"
    if lane.startswith("independent_reviewer/"):
        return "independent_reviewer"
    return "non_owner"


def _grant_lanes(grant: ScopedAuthorityGrant) -> frozenset[str]:
    return frozenset(
        _COMMAND_LANE[identity.command_type]
        for identity in grant.allowed_commands
        if identity.command_type in _COMMAND_LANE
    )


def _parse_supported_scoped_grant(value: object) -> ScopedAuthorityGrant:
    """Parse a persisted scoped grant against its exact supported schema identity."""

    if not isinstance(value, dict):
        raise ValueError("scoped authority grant must be an object")
    schema_id = value.get("schema_id")
    schema_version = value.get("schema_version")
    if not is_scoped_authority_grant_schema(schema_id, schema_version):
        raise ValueError("unsupported scoped authority grant schema")
    return ScopedAuthorityGrant.from_dict(
        value,
        expected_schema_id=str(schema_id),
        expected_schema_version=str(schema_version),
    )


def _role_families_conflict(proposed: frozenset[str], existing: frozenset[str]) -> bool:
    if "owner" in proposed and existing - {"owner"}:
        return True
    if "owner" in existing and proposed - {"owner"}:
        return True
    return bool(
        ("producer" in proposed and "independent_reviewer" in existing)
        or ("independent_reviewer" in proposed and "producer" in existing)
    )


def _deterministic_id(kind: str, prefix: str, preimage: object) -> str:
    """Derive a stable UUIDv7-shaped identity from canonical semantic bytes."""

    digest = bytearray(hashlib.sha256(canonical_bytes({"kind": kind, "preimage": preimage})).digest()[:16])
    digest[6] = (digest[6] & 0x0F) | 0x70
    digest[8] = (digest[8] & 0x3F) | 0x80
    return f"{prefix}_{uuid.UUID(bytes=bytes(digest))}"


def _utc_text(value: object, *, field: str) -> tuple[datetime, str]:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ConfigurationError(f"{field} must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ConfigurationError(f"{field} must be a canonical UTC timestamp") from exc
    canonical = parsed.isoformat().replace("+00:00", "Z")
    if parsed.tzinfo != UTC or canonical != value:
        raise ConfigurationError(f"{field} must be a canonical UTC timestamp")
    return parsed, canonical


def _git(repository_root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(  # nosec B603 - fixed executable and caller-independent argv
            ["git", "-C", str(repository_root), *arguments],
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigurationError("SPEC route Git identity is unavailable") from exc
    return completed.stdout.strip()


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()  # nosec B324


def _load_route(repository_root: Path) -> frozenset[str]:
    top = Path(_git(repository_root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != repository_root:
        raise ConfigurationError("repository_root is not the exact Git worktree root")
    if _git(repository_root, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise ConfigurationError("repository_root is not clean")
    route_path = repository_root / _ROUTE_RELATIVE
    schema_path = repository_root / _ROUTE_SCHEMA_RELATIVE
    catalogue_path = repository_root / _CATALOGUE_RELATIVE
    try:
        route_raw, schema_raw, catalogue_raw = (
            route_path.read_bytes(),
            schema_path.read_bytes(),
            catalogue_path.read_bytes(),
        )
        route, schema, catalogue = map(json.loads, (route_raw, schema_raw, catalogue_raw))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("SPEC route authority material is invalid") from exc
    for relative, raw in (
        (_ROUTE_RELATIVE, route_raw),
        (_ROUTE_SCHEMA_RELATIVE, schema_raw),
        (_CATALOGUE_RELATIVE, catalogue_raw),
    ):
        if _git(repository_root, "rev-parse", "--verify", f"HEAD:{relative.as_posix()}") != _git_blob(raw):
            raise ConfigurationError("SPEC route authority material is not committed at HEAD")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(route)
    except (JsonSchemaError, ValidationError) as exc:
        raise ConfigurationError("SPEC route contract is invalid") from exc
    if (
        route.get("route_id") != "SPEC-GATE6-RUN-V1"
        or route.get("activation_status") != "inert_proposed"
        or route.get("authority_activation") != "forbidden"
        or not all(route.get("prohibitions", {}).values())
    ):
        raise ConfigurationError("SPEC route contract authority boundary mismatch")
    rows = {row["owner_row_id"]: row for row in catalogue.get("owner_contract_rows", [])}
    derived: list[str] = []
    route_contexts: dict[str, set[tuple[str, str]]] = {}
    try:
        for step in route["route_steps"]:
            for row_id in step["owner_rows"]:
                command_type = rows[row_id]["command_type"]
                route_contexts.setdefault(command_type, set()).add((step["stage"], rows[row_id]["eligible_profile"]))
                if command_type not in derived:
                    derived.append(command_type)
    except (KeyError, TypeError) as exc:
        raise ConfigurationError("SPEC route command derivation failed") from exc
    if route.get("governed_command_types") != derived:
        raise ConfigurationError("SPEC route governed commands are not independently derived")
    lane_commands = [command for commands in _LANE_COMMAND_POLICY.values() for command in commands]
    route_lane_commands = [
        command
        for lane, commands in _LANE_COMMAND_POLICY.items()
        if lane not in _SPEC_FLOW_SUPPORT_LANES
        for command in commands
    ]
    if len(lane_commands) != len(set(lane_commands)) or set(route_lane_commands) != set(derived):
        raise ConfigurationError("SPEC route authority lane policy does not partition the accepted commands")
    for lane, commands in _LANE_COMMAND_POLICY.items():
        if lane in _SPEC_FLOW_SUPPORT_LANES:
            continue
        stages, profiles = _LANE_CONTEXT_POLICY[lane]
        if any(
            not any(stage in stages and profile in profiles for stage, profile in route_contexts[command])
            for command in commands
        ):
            raise ConfigurationError("SPEC route authority lane role/stage binding mismatch")
    support_commands = {command for lane in _SPEC_FLOW_SUPPORT_LANES for command in _LANE_COMMAND_POLICY[lane]}
    return frozenset(derived) | support_commands


def _enforce_durable_role_independence(
    *,
    root: Path,
    objects: ObjectStore,
    resolver: LedgerAuthorityGrantResolver,
    proposed_grant: ScopedAuthorityGrant,
    now: datetime,
) -> None:
    """Reject incompatible active roles for one actor using verified grant replay."""

    proposed_families = frozenset(_lane_family(lane) for lane in _grant_lanes(proposed_grant))
    governed_grant_ids = resolver.owner_published_grant_ids()
    grant_root = _physical_directory(root / "objects/authority_grant", label="authority grant objects")
    try:
        candidates = tuple(grant_root.iterdir())
    except OSError as exc:
        raise ConfigurationError("authority grant objects are unreadable") from exc
    for candidate in candidates:
        if candidate.name == proposed_grant.authority_grant_id:
            continue
        _require_bounded_target(
            root,
            Path("objects/authority_grant") / candidate.name,
            label="existing scoped authority grant object",
        )
        try:
            value = objects.read("authority_grant", candidate.name, 1)
        except ValueError:
            continue
        if not isinstance(value, dict) or not is_scoped_authority_grant_schema(
            value.get("schema_id"), value.get("schema_version")
        ):
            continue
        try:
            existing = _parse_supported_scoped_grant(value)
        except ValueError as exc:
            raise IntegrityError("existing scoped authority grant object is invalid") from exc
        if existing.actor_id != proposed_grant.actor_id or not existing.allowed_commands:
            continue
        if existing.authority_grant_id not in governed_grant_ids:
            continue
        try:
            resolver.resolve_command(
                existing.authority_grant_id,
                existing.actor_id,
                existing.allowed_actor_classes[0],
                existing.allowed_commands[0],
                "R0",
                existing.subject_scope.project_id,
                existing.subject_scope.subject_kind,
                existing.subject_scope.subject_id,
                now,
            )
        except ArsError as exc:
            if str(exc) in _INACTIVE_GRANT_ERRORS:
                continue
            raise
        existing_families = frozenset(_lane_family(lane) for lane in _grant_lanes(existing))
        if _role_families_conflict(proposed_families, existing_families):
            raise ArsError("SPEC route actor has an incompatible active authority role")


def _known_authority_actor_classes(
    root: Path,
    objects: ObjectStore,
    *,
    now: datetime | None = None,
    project_id: str | None = None,
    store_identity: str | None = None,
    owner_actor_id: str | None = None,
) -> dict[str, frozenset[str]]:
    actors: dict[str, set[str]] = {}
    governed_actor_ids: set[str] = set()
    current_registered_actors: dict[str, set[str]] = {}
    grant_root = _physical_directory(root / "objects/authority_grant", label="authority grant objects")
    for candidate in grant_root.iterdir():
        _require_bounded_target(
            root,
            Path("objects/authority_grant") / candidate.name,
            label="configured authority grant object",
        )
        try:
            value = objects.read("authority_grant", candidate.name, 1)
            if is_scoped_authority_grant_schema(value.get("schema_id"), value.get("schema_version")):
                grant = _parse_supported_scoped_grant(value)
                actors.setdefault(grant.actor_id, set()).update(grant.allowed_actor_classes)
            else:
                grant = AuthorityGrant.from_dict(value)
                actors.setdefault(grant.actor_id, set()).add("human")
        except (TypeError, ValueError) as exc:
            raise IntegrityError("configured authority actor evidence is invalid") from exc
    # Governed Codex Desktop registrations are immutable evidence in the
    # assurance-record object family.  They supplement (and never replace)
    # the historical grant-derived actor classes above.
    from research_system.authority_actor import ACTOR_SCHEMA_ID, REGISTRATION_SCHEMA_ID

    registration_root = _physical_directory(root / "objects/assurance_record", label="actor registration objects")
    effective_now = now or datetime.now(UTC)
    for candidate in registration_root.iterdir():
        _require_bounded_target(
            root,
            Path("objects/assurance_record") / candidate.name,
            label="actor registration object",
        )
        try:
            validate_id(candidate.name, "assurance_record")
        except ValueError:
            raise IntegrityError("configured actor registration identity is invalid")
        # Assurance records also contain owner-publication objects.  Peek at
        # the raw JSON marker first so unrelated records (including an object
        # left in a recovery state) remain available to their existing
        # recovery validator instead of being parsed as actor registrations.
        registration_marker = None
        try:
            revision_paths = sorted(candidate.glob("*.json"))
        except OSError as exc:
            raise IntegrityError("configured actor registration evidence is unavailable") from exc
        for revision_path in revision_paths:
            try:
                raw = revision_path.read_bytes()
                parsed = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(parsed, dict) and parsed.get("schema_id") == REGISTRATION_SCHEMA_ID:
                registration_marker = revision_path
                break
        if registration_marker is None:
            continue
        _require_bounded_object_revision(
            root,
            "assurance_record",
            candidate.name,
            1,
            label="actor registration object",
        )
        revision = objects.latest_revision("assurance_record", candidate.name)
        if revision is None:
            continue
        value = objects.read("assurance_record", candidate.name, revision)
        if not isinstance(value, dict) or value.get("schema_id") != REGISTRATION_SCHEMA_ID:
            continue
        required = {
            "schema_id",
            "schema_version",
            "registration_id",
            "project_id",
            "store_identity",
            "owner_actor_id",
            "owner_action",
            "idempotency_key",
            "command_payload_hash",
            "actor_id",
            "actor_sha256",
            "semantic_intent",
            "accepted_at",
            "revoked",
        }
        if (
            set(value) != required
            or value.get("schema_version") != "1.0.0"
            or value.get("registration_id") != candidate.name
            or value.get("revoked") is not False
        ):
            raise IntegrityError("configured actor registration evidence is invalid")
        if (
            (project_id is not None and value.get("project_id") != project_id)
            or (store_identity is not None and value.get("store_identity") != store_identity)
            or (owner_actor_id is not None and value.get("owner_actor_id") != owner_actor_id)
        ):
            continue
        semantic = value.get("semantic_intent")
        if not isinstance(semantic, dict) or semantic.get("app_family") != "codex_desktop":
            raise IntegrityError("configured actor registration evidence is invalid")
        try:
            effective = datetime.fromisoformat(str(semantic["effective_at"]).replace("Z", "+00:00"))
            expires = datetime.fromisoformat(str(semantic["expires_at"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("configured actor registration time is invalid") from exc
        actor_id = value.get("actor_id")
        _require_bounded_target(
            root,
            Path("objects/canonical_actor") / str(actor_id),
            label="canonical actor object",
        )
        actor_revision = objects.latest_revision("canonical_actor", str(actor_id))
        if actor_revision is None:
            raise IntegrityError("configured actor registration actor object is missing")
        actor = objects.read("canonical_actor", str(actor_id), actor_revision)
        if (
            not isinstance(actor, dict)
            or actor.get("schema_id") != ACTOR_SCHEMA_ID
            or actor.get("actor_id") != actor_id
            or actor.get("registration_id") != value.get("registration_id")
            or actor.get("revoked") is not False
            or (project_id is not None and actor.get("project_id") != project_id)
            or (store_identity is not None and actor.get("store_identity") != store_identity)
            or (owner_actor_id is not None and actor.get("owner_actor_id") != owner_actor_id)
            or sha256_hex(canonical_bytes(actor)) != value.get("actor_sha256")
            or semantic != {key: actor.get(key) for key in semantic}
        ):
            raise IntegrityError("configured actor registration actor evidence is invalid")
        actor_class = semantic.get("actor_class")
        if actor_class not in {"agent", "service"}:
            raise IntegrityError("configured actor registration class is invalid")
        governed_actor_ids.add(str(actor_id))
        if effective.tzinfo != UTC or expires.tzinfo != UTC or not effective <= effective_now < expires:
            continue
        current_registered_actors.setdefault(str(actor_id), set()).add(str(actor_class))
    # Once an actor has governed registration evidence, that registration is
    # the authority for session currency.  Historical grants must not keep an
    # expired registered session eligible for a fresh grant.
    for actor_id in governed_actor_ids:
        actors.pop(actor_id, None)
    for actor_id, classes in current_registered_actors.items():
        actors.setdefault(actor_id, set()).update(classes)
    return {actor_id: frozenset(classes) for actor_id, classes in actors.items()}


def _registered_actor_lane_is_compatible(objects: ObjectStore, actor_id: str, authority_lane: str) -> bool:
    """Keep governed session roles from crossing operator/reviewer/producer boundaries."""

    from research_system.authority_actor import ACTOR_SCHEMA_ID

    revision = objects.latest_revision("canonical_actor", actor_id)
    if revision is None:
        return True  # Historical grant-derived actors remain governed by their active grants.
    actor = objects.read("canonical_actor", actor_id, revision)
    if not isinstance(actor, Mapping) or actor.get("schema_id") != ACTOR_SCHEMA_ID:
        return True
    role = actor.get("actor_role")
    if role == "independent_reviewer":
        return authority_lane.startswith("independent_reviewer/")
    if role == "operator":
        return authority_lane.startswith("operator/")
    if role == "producer":
        return not authority_lane.startswith(("independent_reviewer/", "operator/", "owner_decider/"))
    return False


class _RoleSeparatedAuthorityCommandService(CommandService):
    """Recheck actor-role independence inside CommandService's writer lock."""

    def __init__(
        self,
        *args: Any,
        role_validator: Callable[[object], None],
        decision_path_validator: Callable[[object], None],
        publication_preparer: Callable[[Any], dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._role_validator = role_validator
        self._decision_path_validator = decision_path_validator
        self._publication_preparer = publication_preparer

    def _before_authority_resolution(self, command: Any) -> None:
        if command.envelope.get("command_type") == "ActivateAuthorityGrant":
            payload = command.envelope.get("payload", {})
            self._decision_path_validator(payload.get("administration_decision_id"))
            self._role_validator(payload.get("new_grant"))

    def _prepare_owner_authority_publication(self, command: Any, observed_version: int) -> dict[str, Any]:
        del observed_version
        return self._publication_preparer(command)


@dataclass(frozen=True)
class OwnerAuthoritySetup:
    root: Path
    schemas: SchemaRegistry
    resolver: LedgerAuthorityGrantResolver
    service: CommandService
    objects: ObjectStore
    route_commands: frozenset[str]
    clock: Callable[[], datetime]

    def register_actor(self, intent: object) -> dict[str, Any]:
        """Register one real Codex Desktop session from semantic owner intent."""
        from research_system.authority_actor import RegisterAuthorityActor, register_authority_actor

        if not isinstance(intent, RegisterAuthorityActor):
            raise ArsError("authority actor registration requires typed owner intent")
        return register_authority_actor(
            intent,
            root=self.root,
            project_id=self.resolver.administration_context().project_id,
            store_identity=str(self.resolver.administration_context().store_identity),
            schemas=self.schemas,
            resolver=self.resolver,
            objects=self.objects,
            route_commands=self.route_commands,
            clock=self.clock,
        )

    def _check_role_independence(self, grant: ScopedAuthorityGrant) -> None:
        _enforce_durable_role_independence(
            root=self.root,
            objects=self.objects,
            resolver=self.resolver,
            proposed_grant=grant,
            now=self.clock(),
        )

    def _grant(self, value: object, *, authority_lane: object) -> tuple[ScopedAuthorityGrant, str]:
        context = self.resolver.administration_context()
        try:
            grant = ScopedAuthorityGrant.from_dict(value)
            identity = self.schemas.resolve_identity(
                SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
                SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
            )
            self.schemas.validate_active(
                identity.schema_id,
                value,
                schema_version=identity.schema_version,
                expected_sha256=identity.sha256,
            )
            validate_scoped_grant_activation(
                grant,
                self.schemas,
                owner_actor_id=context.owner_actor_id,
            )
        except (ArsError, SchemaError, TypeError, ValueError) as exc:
            raise ArsError("proposed scoped authority grant is invalid") from exc
        commands = {item.command_type for item in grant.allowed_commands}
        lane_commands = _LANE_COMMAND_POLICY.get(authority_lane) if isinstance(authority_lane, str) else None
        if (
            not commands
            or grant.allowed_policy_actions
            or len(grant.allowed_actor_classes) != 1
            or not commands <= self.route_commands
            or lane_commands is None
            or not commands <= lane_commands
            or grant.allowed_actor_classes[0] not in _LANE_ALLOWED_ACTOR_CLASSES[str(authority_lane)]
        ):
            raise ArsError("proposed grant exceeds the independently verified SPEC route")
        if authority_lane.startswith("owner_decider/"):
            if grant.actor_id != context.owner_actor_id or grant.allowed_actor_classes != ("human",):
                raise ArsError("owner decision lane requires the bound human owner")
        elif grant.actor_id == context.owner_actor_id:
            raise ArsError("non-owner SPEC route lanes cannot be assigned to the bound owner")
        return grant, identity.sha256

    def _derive_publication_material(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Independently derive all internal authority bytes from semantic intent."""

        if set(request) != _PUBLISH_FIELDS or request.get("owner_action") != "activate_authority_grant":
            raise ArsError("owner authority publication intent is invalid")
        retry_key = request.get("retry_key")
        evidence_refs = request.get("evidence_refs")
        reason = request.get("reason")
        if not isinstance(retry_key, str) or not retry_key or not isinstance(reason, str) or not reason:
            raise ConfigurationError("authority intent retry_key and reason must be non-empty")
        if (
            not isinstance(evidence_refs, list)
            or not evidence_refs
            or not all(isinstance(item, str) and item for item in evidence_refs)
        ):
            raise ConfigurationError("authority intent evidence_refs must be non-empty strings")
        lane = request.get("authority_lane")
        actor_role = request.get("actor_role")
        lane_commands = _LANE_COMMAND_POLICY.get(lane) if isinstance(lane, str) else None
        lane_context = _LANE_CONTEXT_POLICY.get(lane) if isinstance(lane, str) else None
        if lane_commands is None or lane_context is None or actor_role not in lane_context[1]:
            raise ArsError("authority intent lane and actor role do not match the SPEC route")
        actor_class = request.get("target_actor_class")
        if actor_class not in _LANE_ALLOWED_ACTOR_CLASSES[str(lane)]:
            raise ArsError("authority intent actor class does not match the SPEC route")
        subject_scope = request.get("subject_scope")
        subject = subject_scope.get("subject") if isinstance(subject_scope, dict) else None
        subject_kind = subject.get("kind") if isinstance(subject, dict) else None
        if not isinstance(subject_kind, str):
            raise ArsError("authority intent subject scope is invalid")
        command_types = tuple(
            sorted(
                command_type
                for command_type in lane_commands
                if _SCOPED_COMMAND_SUBJECT_KINDS.get(command_type) == subject_kind
            )
        )
        if not command_types:
            raise ArsError("authority intent lane has no command for the subject kind")
        effective_at, effective_text = _utc_text(request.get("effective_at"), field="effective_at")
        expires_at, expires_text = _utc_text(request.get("expires_at"), field="expires_at")
        now = self.clock()
        if now.tzinfo != UTC or not effective_at <= now < expires_at or effective_at >= expires_at:
            raise ArsError("owner authority intent window is not current and finite")
        context = self.resolver.administration_context()
        known = _known_authority_actor_classes(
            self.root,
            self.objects,
            now=now,
            project_id=str(context.project_id),
            store_identity=str(context.store_identity),
            owner_actor_id=str(context.owner_actor_id),
        )
        if actor_class not in known.get(str(request.get("target_actor_id")), ()):
            raise ArsError("authority intent target actor is not a real configured authority actor")
        if not _registered_actor_lane_is_compatible(
            self.objects,
            str(request.get("target_actor_id")),
            lane,
        ):
            raise ArsError("authority intent conflicts with the actor's governed session role")
        semantic_intent = {
            key: json.loads(canonical_bytes(value)) for key, value in request.items() if key != "retry_key"
        }
        grant_id = _deterministic_id("owner-authority-grant", "agr", semantic_intent)
        decision_id = _deterministic_id("owner-authority-decision", "arec", semantic_intent)
        allowed_commands = []
        for command_type in command_types:
            identity = self.schemas.command_binding(command_type)
            if identity is None or not self.schemas.is_active(identity.schema_id, identity.schema_version):
                raise ArsError("SPEC route command schema is not active")
            resolved = self.schemas.resolve_identity(identity.schema_id, identity.schema_version)
            allowed_commands.append(
                {
                    "command_type": command_type,
                    "schema_id": resolved.schema_id,
                    "schema_version": str(resolved.schema_version),
                    "schema_sha256": resolved.sha256,
                }
            )
        grant_value = {
            "schema_id": SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
            "schema_version": SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
            "authority_grant_id": grant_id,
            "actor_id": request["target_actor_id"],
            "allowed_actor_classes": [actor_class],
            "allowed_commands": allowed_commands,
            "allowed_policy_actions": [],
            "subject_scope": request["subject_scope"],
            "risk_ceiling": _LANE_RISK_POLICY[str(lane)],
            "effective_at": effective_text,
            "expires_at": expires_text,
            "delegable": False,
            "revoked": False,
        }
        grant, grant_schema_sha256 = self._grant(grant_value, authority_lane=lane)
        decision_value = {
            "schema_id": OWNER_AUTHORITY_DECISION_SCHEMA_ID,
            "schema_version": OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
            "record_id": decision_id,
            "revision": 1,
            "project_id": context.project_id,
            "store_identity": str(context.store_identity),
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "owner_actor_id": context.owner_actor_id,
            "action": "activate_authority_grant",
            "target_grant_id": grant.authority_grant_id,
            "target_grant_sha256": grant.canonical_sha256,
            "target_grant_schema_id": SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
            "target_grant_schema_version": SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
            "target_grant_schema_sha256": grant_schema_sha256,
            "subject_scope": grant.subject_scope.to_dict(),
            "effective_at": effective_text,
            "expires_at": expires_text,
            "one_time_use": True,
            "state": "active",
            "decided_at": effective_text,
        }
        self.schemas.validate_active(
            OWNER_AUTHORITY_DECISION_SCHEMA_ID,
            decision_value,
            schema_version=OWNER_AUTHORITY_DECISION_SCHEMA_VERSION,
        )
        decision = OwnerAuthorityAdministrationDecision.from_dict(decision_value)
        self._check_role_independence(grant)
        return {
            "context": context,
            "semantic_intent": semantic_intent,
            "grant": grant,
            "grant_value": grant_value,
            "decision": decision,
            "decision_value": decision_value,
            "authority_lane": lane,
            "effective_at": effective_text,
        }

    def publish(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Derive and govern one owner decision from meaningful owner intent."""

        material = self._derive_publication_material(request)
        retry_key = str(request["retry_key"])
        reason = str(request["reason"])
        evidence_refs = list(request["evidence_refs"])
        context = material["context"]
        semantic_intent = material["semantic_intent"]
        grant = material["grant"]
        decision = material["decision"]
        lane = material["authority_lane"]
        effective_text = material["effective_at"]
        command_id = _deterministic_id("owner-authority-publication-command", "cmd", retry_key)
        command = {
            "command_id": command_id,
            "command_type": "PublishOwnerAuthorityAdministrationDecision",
            "schema_id": "ars://core/command/PublishOwnerAuthorityAdministrationDecision",
            "schema_version": "1.0.0",
            "submitted_at": effective_text,
            "actor_id": context.owner_actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": context.root_grant_id,
            "target_stream_id": decision.record_id,
            "expected_stream_version": 0,
            "idempotency_key": retry_key,
            "correlation_id": retry_key,
            "causation_id": None,
            "reason": reason,
            "evidence_refs": list(evidence_refs),
            "project_id": context.project_id,
            "payload": {"intent": semantic_intent},
        }
        receipt = self.service.submit(command)
        return {
            **asdict(receipt),
            "administration_decision_id": decision.record_id,
            "administration_decision_sha256": decision.canonical_sha256,
            "authority_grant_id": grant.authority_grant_id,
            "authority_grant_sha256": grant.canonical_sha256,
            "authority_lane": lane,
        }

    def activate(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if set(request) != _ACTIVATE_FIELDS:
            raise ConfigurationError("authority activate input fields must be exact")
        context = self.resolver.administration_context()
        publication_command_id = request.get("publication_command_id")
        events = [
            event
            for event in self.service.ledger.snapshot().events
            if event.get("command_id") == publication_command_id
            and event.get("event_type") == "OwnerAuthorityAdministrationDecisionPublished"
        ]
        if len(events) != 1:
            raise ArsError("owner authority publication result is unavailable")
        publication = events[0]
        published = publication.get("payload", {})
        decision_value = published.get("decision")
        grant_value = published.get("proposed_grant")
        lane = published.get("authority_lane")
        grant, grant_schema_sha256 = self._grant(grant_value, authority_lane=lane)
        self._check_role_independence(grant)
        decision = OwnerAuthorityAdministrationDecision.from_dict(decision_value)
        decision_id = decision.record_id
        evidence_refs = request["evidence_refs"]
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ArsError("owner authority administration decision evidence missing")
        _require_bounded_target(
            self.root,
            Path("objects/authority_grant") / grant.authority_grant_id,
            label="scoped authority grant object",
        )
        _require_bounded_target(
            self.root,
            Path("events") / context.project_id / "authority_grant" / grant.authority_grant_id,
            label="scoped authority event stream",
        )
        _require_bounded_object_revision(
            self.root,
            "assurance_record",
            str(decision_id),
            1,
            label="owner decision object",
        )
        stored_decision = self.objects.read("assurance_record", str(decision_id), 1)
        decision_sha256 = sha256_hex(canonical_bytes(stored_decision))
        command_id = _deterministic_id("owner-authority-activation-command", "cmd", request["retry_key"])
        command = {
            "command_id": command_id,
            "command_type": "ActivateAuthorityGrant",
            "schema_id": "ars://core/command/ActivateAuthorityGrant",
            "schema_version": "1.1.0",
            "submitted_at": publication["recorded_at"],
            "actor_id": context.owner_actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": context.root_grant_id,
            "target_stream_id": grant.authority_grant_id,
            "expected_stream_version": 0,
            "idempotency_key": request["retry_key"],
            "correlation_id": request["retry_key"],
            "causation_id": publication_command_id,
            "reason": request["reason"],
            "evidence_refs": [*evidence_refs, decision_id],
            "project_id": context.project_id,
            "payload": {
                "project_id": context.project_id,
                "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
                "root_grant_id": context.root_grant_id,
                "root_grant_sha256": context.root_grant_sha256,
                "administration_decision_id": decision_id,
                "administration_decision_sha256": decision_sha256,
                "new_grant": json.loads(canonical_bytes(grant_value)),
                "new_grant_sha256": grant.canonical_sha256,
                "new_grant_schema_sha256": grant_schema_sha256,
            },
        }
        return asdict(self.service.submit(command))


def load_owner_authority_setup(
    config_path: Path,
    *,
    clock: Callable[[], datetime] | None = None,
) -> OwnerAuthoritySetup:
    """Validate route, physical store, binding, and replay before opening writers."""

    config = _read_canonical_object(Path(config_path).resolve(strict=True), label="authority setup config")
    if set(config) != _CONFIG_FIELDS:
        raise ConfigurationError("authority setup config fields must be exact")
    repository_root = _physical_directory(Path(config["repository_root"]), label="repository_root")
    try:
        binding = ControlBinding.load(Path(config["authority_binding"]))
    except ConfigurationError:
        binding = ControlBinding.load_repaired(Path(config["authority_binding"]))
    if repository_root not in {Path(path).resolve(strict=True) for path in binding.code_roots}:
        raise ConfigurationError("repository_root is not bound by authority configuration")
    authority_root = _physical_directory(Path(binding.control_root), label="authority store")
    _require_authority_layout(authority_root, binding.project_id)
    route_commands = _load_route(repository_root)
    schemas = runtime_schema_registry(binding.schema_root)
    resolver = LedgerAuthorityGrantResolver(
        authority_root,
        binding.project_id,
        binding.store_identity,
        schemas,
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    resolver.administration_context()
    objects = ObjectStore(authority_root)
    selected_clock = clock or (lambda: datetime.now(UTC))

    def locked_role_validator(value: object) -> None:
        try:
            proposed = ScopedAuthorityGrant.from_dict(value)
        except ValueError as exc:
            raise ArsError("proposed scoped authority grant is invalid") from exc
        _enforce_durable_role_independence(
            root=authority_root,
            objects=objects,
            resolver=resolver,
            proposed_grant=proposed,
            now=selected_clock(),
        )

    def locked_decision_path_validator(value: object) -> None:
        if not isinstance(value, str):
            raise ArsError("owner authority administration decision identity is invalid")
        _require_bounded_object_revision(
            authority_root,
            "assurance_record",
            value,
            1,
            label="owner decision object",
        )

    setup: OwnerAuthoritySetup | None = None

    def locked_publication_preparer(command: Any) -> dict[str, Any]:
        if setup is None:
            raise IntegrityError("semantic authority setup is unavailable")
        payload = command.envelope.get("payload")
        semantic_intent = payload.get("intent") if isinstance(payload, dict) else None
        if (
            not isinstance(payload, dict)
            or set(payload) != {"intent"}
            or not isinstance(semantic_intent, dict)
            or set(semantic_intent) != _PUBLISH_FIELDS - {"retry_key"}
        ):
            raise ArsError("owner authority publication requires exact semantic intent")
        request = {
            "retry_key": command.idempotency_key,
            **json.loads(canonical_bytes(semantic_intent)),
        }
        material = setup._derive_publication_material(request)
        context = material["context"]
        decision = material["decision"]
        effective_at = material["effective_at"]
        expected_command_id = _deterministic_id(
            "owner-authority-publication-command",
            "cmd",
            command.idempotency_key,
        )
        if (
            command.command_id != expected_command_id
            or command.target_stream_id != decision.record_id
            or command.expected_stream_version != 0
            or command.actor_id != context.owner_actor_id
            or command.envelope.get("on_behalf_of_actor_id") is not None
            or command.envelope.get("authority_grant_id") != context.root_grant_id
            or command.envelope.get("project_id") != context.project_id
            or command.envelope.get("submitted_at") != effective_at
            or command.envelope.get("correlation_id") != command.idempotency_key
            or command.envelope.get("causation_id") is not None
            or command.envelope.get("reason") != semantic_intent["reason"]
            or command.envelope.get("evidence_refs") != semantic_intent["evidence_refs"]
        ):
            raise ArsError("owner authority publication envelope does not match derived intent")
        return {
            "project_id": context.project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "authority_lane": material["authority_lane"],
            "actor_role": semantic_intent["actor_role"],
            "decision": material["decision_value"],
            "proposed_grant": material["grant_value"],
        }

    service = _RoleSeparatedAuthorityCommandService(
        authority_root,
        EventLedger(authority_root, binding.project_id, schemas),
        objects,
        ReceiptStore(authority_root),
        schemas,
        authority_resolver=resolver,
        clock=selected_clock,
        role_validator=locked_role_validator,
        decision_path_validator=locked_decision_path_validator,
        publication_preparer=locked_publication_preparer,
    )
    setup = OwnerAuthoritySetup(authority_root, schemas, resolver, service, objects, route_commands, selected_clock)
    return setup
