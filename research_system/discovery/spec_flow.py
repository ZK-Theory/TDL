"""Provider-free operator coordinator for the governed Gate 6 SPEC route.

The coordinator owns no research execution and no second lifecycle state
machine.  Durable lifecycle truth is replayed from the Discovery ledger; an
advance packet merely supplies the real identities, authority references, and
evidence required by the one next route action.
"""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.command.service import CommandService
from research_system.artefacts.authority import ArtefactAuthorityContractLoader
from research_system.artefacts.runtime import (
    ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT,
    ControlRootArtefactContentReader,
    GoverningScientificReviewStore,
)
from research_system.artefacts.use_resolver import ArtefactUseResolver
from research_system.context.registry import resolve_context_packet_for_consumer
from research_system.context.spec_bridge import deliver_spec_owner_context
from research_system.discovery.operator import DiscoveryOperator
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierMember,
    accepted_expected_set_hash,
)
from research_system.discovery.authority import (
    PORTABLE_SPEC_REQUIRED_MEMBERS,
    validate_portable_path_subject,
)
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.routes import discovery_route
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    register_candidate_document,
)
from research_system.methods.registration import RawContentPublication, publish_registered_raw_content
from research_system.evidence.consumers import ArtefactEvidenceConsumers
from research_system.methods.brief import export_brief
from research_system.methods.pack import load_methods_pack
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


ROUTE_ID = "SPEC-GATE6-RUN-V1"
_ROUTE_PATH = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
_SPEC_01_PATH = _ROUTE_PATH.parent / "spec-01-assay-brief-v1.1.0.md"
_SPEC_02_PATH = _ROUTE_PATH.parent / "spec-02-micro-spike-contract-v1.1.0.md"
_DOSSIER_AUTHORITY_PATH = _ROUTE_PATH.parent / "spec-dossier-expected-set-authority.json"
_PATH_AUTHORITY_PATH = _ROUTE_PATH.parent / "spec-path-registration-authority.json"
_DOSSIER_MANIFEST_PATH = _ROUTE_PATH.parent / "spec-research-dossier-manifest.json"
_PACKET_FIELDS = frozenset(
    {"schema_id", "schema_version", "route_id", "action", "retry_id", "commands", "document", "registration"}
)
_REGISTRATION_FIELDS = frozenset(
    {
        "artefact_id",
        "project_id",
        "actor_id",
        "authority_grant_id",
        "submitted_at",
        "correlation_id",
        "reason",
        "manifest",
    }
)

_ACTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bootstrap_genesis", ("OR-140",)),
    ("bootstrap_assay_authority", tuple(f"OR-{value:03d}" for value in range(101, 109))),
    ("bootstrap_dossier_authority", tuple(f"OR-{value:03d}" for value in range(110, 116))),
    ("bootstrap_path_authority", tuple(f"OR-{value:03d}" for value in range(116, 122))),
    ("admit_dossier", ("OR-028",)),
    ("observe_source", ("OR-029",)),
    ("request_spec_01", ("OR-003",)),
)
_COMMAND_ACTION_ROWS = dict(_ACTIONS)
_COMMAND_ACTION_ROWS.update(
    {
        "return_spec_01_complete": ("OR-004",),
        "return_spec_01_partial": ("OR-005",),
        "review_spec_01_complete": ("OR-034", "OR-006"),
        "review_spec_01_partial": ("OR-035", "OR-007"),
        "decide_spec_01": ("OR-012", "OR-013"),
        "start_spec_02": ("OR-014", "OR-015", "OR-016", "OR-017"),
        "return_spec_02_complete": ("OR-018",),
        "return_spec_02_partial": ("OR-019",),
        "review_spec_02_complete": ("OR-036", "OR-020"),
        "review_spec_02_partial": ("OR-037", "OR-021"),
        "decide_spec_02": ("OR-026", "OR-027"),
    }
)
_DOCUMENT_ACTION_SCHEMA = {
    "prepare_spec_01": "ars://portfolio/spec-operator-brief-package",
    "return_spec_01_complete": "ars://portfolio/spec-operator-return",
    "return_spec_01_partial": "ars://portfolio/spec-operator-return",
    "approve_spec_02": "ars://portfolio/spec-02-live-run-approval",
    "prepare_spec_02": "ars://portfolio/spec-operator-brief-package",
    "return_spec_02_complete": "ars://portfolio/spec-operator-return",
    "return_spec_02_partial": "ars://portfolio/spec-operator-return",
}
_DOCUMENT_TYPES = {
    "prepare_spec_01": "spec_01_operator_brief",
    "return_spec_01_complete": "spec_01_return",
    "return_spec_01_partial": "spec_01_return",
    "approve_spec_02": "spec_02_live_run_approval",
    "prepare_spec_02": "spec_02_operator_brief",
    "return_spec_02_complete": "spec_02_return",
    "return_spec_02_partial": "spec_02_return",
}
_BRIEF_INPUT_TYPES = {"spec_operator_source", "methods_asset"}


@dataclass(frozen=True)
class SpecFlowStatus:
    capability_state: str
    completed_stage: str
    next_action: str | None
    block_reason: str | None
    route_id: str = ROUTE_ID


def _git(repository_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(  # nosec B603 B607 - fixed Git executable and arguments
            ["git", "-C", str(repository_root), *arguments],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ConfigurationError("SPEC route Git binding is unavailable") from exc
    if result.returncode != 0:
        raise ConfigurationError("SPEC route is not committed at operator HEAD")
    return result.stdout.strip()


def build_spec_authority_subject(repository_root: Path, authority_kind: str) -> dict[str, Any]:
    """Build one proposed SPEC authority subject from exact committed route bytes.

    The portable path subject remains byte-stable. OR-117 separately binds the
    clean checkout's physical directory identity before it can be accepted.
    """

    if authority_kind not in {"dossier_expected_set", "path_registration"}:
        raise ValueError("unsupported SPEC authority kind")
    authority_path = _DOSSIER_AUTHORITY_PATH if authority_kind == "dossier_expected_set" else _PATH_AUTHORITY_PATH
    try:
        subject = json.loads((repository_root / authority_path).read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("proposed SPEC authority is unavailable") from exc
    if not isinstance(subject, dict) or subject.get("authority_kind") != authority_kind:
        raise ConfigurationError("proposed SPEC authority kind differs")
    if authority_kind == "dossier_expected_set":
        expected_value = subject.get("expected_set")
        if not isinstance(expected_value, dict) or not isinstance(expected_value.get("members"), list):
            raise ConfigurationError("proposed SPEC expected set is malformed")
        expected = AcceptedExpectedSet(
            **{
                **expected_value,
                "members": tuple(DossierMember(**member) for member in expected_value["members"]),
            }
        )
        if accepted_expected_set_hash(expected) != expected.content_hash:
            raise ConfigurationError("proposed SPEC expected-set hash differs")
        for member in expected.members:
            expected_paths = {
                "route-package": _ROUTE_PATH,
                "SPEC-01": _SPEC_01_PATH,
                "SPEC-02": _SPEC_02_PATH,
            }
            if (
                member.root_id != "repository"
                or member.member_key not in expected_paths
                or Path(member.relative_path) != expected_paths[member.member_key]
            ):
                raise ConfigurationError("proposed SPEC expected set includes non-route lineage")
            raw = (repository_root / member.relative_path).read_bytes()
            if len(raw) != member.size_bytes or sha256_hex(raw) != member.sha256:
                raise ConfigurationError("proposed SPEC expected-set member binding differs")
        return subject
    try:
        validate_portable_path_subject(subject)
    except ValueError as exc:
        raise ConfigurationError("proposed SPEC path authority is not portable repository-only") from exc
    content_preimage = {
        key: value
        for key, value in subject.items()
        if key not in {"content_sha256", "subject_sha256"} and not key.startswith("authority_file_")
    }
    if subject.get("content_sha256") != sha256_hex(canonical_bytes(content_preimage)):
        raise ConfigurationError("proposed SPEC portable authority content hash differs")
    expected_bindings = []
    for alias, relative_path in PORTABLE_SPEC_REQUIRED_MEMBERS:
        path = Path(relative_path)
        try:
            raw = (repository_root / path).read_bytes()
        except OSError as exc:
            raise ConfigurationError("proposed SPEC portable member is unavailable") from exc
        expected_bindings.append(
            {
                "alias": alias,
                "relative_path": relative_path,
                "size_bytes": len(raw),
                "sha256": sha256_hex(raw),
                "git_blob": _git(repository_root, "rev-parse", f"HEAD:{relative_path}"),
            }
        )
    if subject.get("required_member_bindings") != expected_bindings:
        raise ConfigurationError("proposed SPEC portable member set differs from exact route bytes")
    return subject


def _validate_route(operator: DiscoveryOperator) -> dict[str, Any]:
    route_path = operator.repository_root / _ROUTE_PATH
    try:
        raw = route_path.read_bytes()
        route = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("SPEC route package is unavailable") from exc
    if not isinstance(route, dict) or route.get("route_id") != ROUTE_ID:
        raise ConfigurationError("SPEC route package is not the exact governed route")
    try:
        operator.schemas.validate("ars://contracts/wp6-6/spec-gate6-route", route, schema_version="1.0.0")
    except SchemaError as exc:
        raise ConfigurationError("SPEC route package schema binding differs") from exc
    if route.get("activation_status") != "inert_proposed" or route.get("authority_activation") != "forbidden":
        raise ConfigurationError("SPEC route package is not inert")
    sources = {item.get("alias"): item for item in route.get("sources", ()) if isinstance(item, dict)}
    for alias, relative in (("SPEC-01", _SPEC_01_PATH), ("SPEC-02", _SPEC_02_PATH)):
        source = sources.get(alias)
        try:
            data = (operator.repository_root / relative).read_bytes()
        except OSError as exc:
            raise ConfigurationError(f"{alias} governed source is unavailable") from exc
        if source is None or source.get("size_bytes") != len(data) or source.get("sha256") != sha256_hex(data):
            raise ConfigurationError(f"{alias} governed source binding differs")
    for relative in (_ROUTE_PATH, _SPEC_01_PATH, _SPEC_02_PATH):
        working_blob = _git(operator.repository_root, "hash-object", "--", relative.as_posix())
        committed_blob = _git(operator.repository_root, "rev-parse", f"HEAD:{relative.as_posix()}")
        if working_blob != committed_blob:
            raise ConfigurationError("SPEC route source is not committed at operator HEAD")
    return route


def _rows(events: Sequence[Mapping[str, Any]], projection: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    ordered: list[str] = []
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        row = payload.get("row_id") or payload.get("owner_row_id")
        if isinstance(row, str) and row not in ordered:
            ordered.append(row)
    if projection is not None:
        assay_authority = projection.get("assay_bar_authority")
        if isinstance(assay_authority, Mapping) and assay_authority.get("status") == "accepted":
            ordered.extend(row for row in (f"OR-{value:03d}" for value in range(101, 109)) if row not in ordered)
        authorities = projection.get("authorities")
        if isinstance(authorities, Mapping):
            for kind, start in (("dossier_expected_set", 110), ("path_registration", 116)):
                authority = authorities.get(kind)
                if isinstance(authority, Mapping) and authority.get("status") == "accepted":
                    ordered.extend(
                        row for row in (f"OR-{value:03d}" for value in range(start, start + 6)) if row not in ordered
                    )
        dossiers = projection.get("dossiers")
        if isinstance(dossiers, Mapping) and dossiers and "OR-028" not in ordered:
            ordered.append("OR-028")
    return tuple(ordered)


def _registered_documents(
    operator: DiscoveryOperator, projection: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    for stream in projection.get("artefact_streams", {}).values():
        if not isinstance(stream, Mapping):
            continue
        manifest = stream.get("manifest")
        if not isinstance(manifest, Mapping) or manifest.get("root_id") != "control":
            continue
        if manifest.get("artefact_type") not in set(_DOCUMENT_TYPES.values()):
            continue
        relative = manifest.get("relative_path")
        digest = manifest.get("content_sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            continue
        path = operator.control_root / relative
        try:
            raw = path.read_bytes()
            value = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise IntegrityError("registered SPEC document is unavailable")
        if raw != canonical_bytes(value) or sha256_hex(raw) != digest:
            raise IntegrityError("registered SPEC document binding differs")
        if isinstance(value, dict) and value.get("route_id") == ROUTE_ID:
            found.setdefault(str(value.get("document_type")), []).append(value)
    for kind, values in found.items():
        if len(values) != 1:
            raise IntegrityError(f"duplicate registered SPEC document: {kind}")
    return found


def _actor_for_row(events: Sequence[Mapping[str, Any]], row: str) -> str | None:
    actors = {
        event.get("actor_id")
        for event in events
        if isinstance(event.get("payload"), Mapping)
        and (event["payload"].get("row_id") == row or event["payload"].get("owner_row_id") == row)
    }
    return next(iter(actors)) if len(actors) == 1 else None


class SpecFlow:
    """One stage-aware, provider-free SPEC route coordinator."""

    def __init__(self, operator: DiscoveryOperator) -> None:
        self.operator = operator
        self.route = _validate_route(operator)

    def _snapshot(self) -> tuple[tuple[dict[str, Any], ...], dict[str, Any], dict[str, list[dict[str, Any]]]]:
        events = tuple(self.operator.ledger.iter_events())
        projection = replay_discovery(events, schemas=self.operator.schemas)
        documents = _registered_documents(self.operator, projection)
        return events, projection, documents

    @staticmethod
    def _brief_input_states(projection: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        return {
            str(stream_id): state
            for stream_id, state in projection.get("artefact_streams", {}).items()
            if isinstance(state, Mapping)
            and isinstance(state.get("manifest"), Mapping)
            and state["manifest"].get("artefact_type") in _BRIEF_INPUT_TYPES
        }

    def status(self) -> SpecFlowStatus:
        events, projection, documents = self._snapshot()
        rows = set(_rows(events, projection))
        completed = "none"
        for action, required in _ACTIONS:
            if not set(required).issubset(rows):
                return SpecFlowStatus(
                    "NOT_RUNNABLE",
                    completed,
                    action,
                    "exact action identities, evidence, and active authority are required",
                )
            completed = action
        brief_inputs = self._brief_input_states(projection)
        input_types = {state["manifest"].get("artefact_type") for state in brief_inputs.values()}
        required_source_hashes = {
            source["sha256"] for source in self.route["sources"] if source["alias"] in {"SPEC-01", "SPEC-02"}
        }
        registered_source_hashes = {
            state.get("content_sha256")
            for state in brief_inputs.values()
            if state["manifest"].get("artefact_type") == "spec_operator_source"
        }
        if input_types != _BRIEF_INPUT_TYPES or registered_source_hashes != required_source_hashes:
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "request_spec_01",
                "register_spec_01_brief_inputs",
                "exact committed SPEC-01/SPEC-02 sources and required Methods Pack assets must be registered",
            )
        if any(not state.get("scientific_reviews") for state in brief_inputs.values()):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "spec_01_brief_inputs_registered",
                "review_spec_01_brief_inputs",
                "registered brief inputs await independent exact-subject use review",
            )
        if any(state.get("use_authority") != "accepted_for_scope" for state in brief_inputs.values()):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "spec_01_brief_inputs_reviewed",
                "accept_spec_01_brief_inputs",
                "reviewed brief inputs await explicit accepted-for-scope authority",
            )
        if "spec_01_operator_brief" not in documents:
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "request_spec_01",
                "prepare_spec_01",
                "Codex desktop brief export and operator session identity are required",
            )
        if not ({"OR-004", "OR-005"} & rows):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "prepare_spec_01",
                "return_spec_01",
                "manually produced SPEC-01 return evidence is required",
            )
        partial_assay = "OR-005" in rows
        review_rows = {"OR-035", "OR-007"} if partial_assay else {"OR-034", "OR-006"}
        if not review_rows.issubset(rows):
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "return_spec_01",
                "review_spec_01",
                "an independent reviewer and exact unchanged subject hash are required",
            )
        if partial_assay:
            return SpecFlowStatus(
                "PROVEN", "spec_01_partial_reviewed", None, "partial SPEC-01 evidence is an explicit terminal stop"
            )
        if not {"OR-012", "OR-013"}.issubset(rows):
            return SpecFlowStatus(
                "OWNER_BLOCKED", "review_spec_01", "decide_spec_01", "explicit owner PROMOTE, PARK, or KILL is required"
            )
        candidate_ids = {
            event.get("payload", {}).get("candidate_id")
            for event in events
            if isinstance(event.get("payload"), Mapping) and event["payload"].get("row_id") == "OR-003"
        }
        candidates = [projection["candidates"].get(value) for value in candidate_ids if isinstance(value, str)]
        if len(candidates) != 1 or not isinstance(candidates[0], Mapping):
            return SpecFlowStatus(
                "NOT_RUNNABLE", "decide_spec_01", None, "exact SPEC route Candidate cannot be resolved"
            )
        candidate_status = candidates[0].get("status")
        if candidate_status in {"parked", "killed"}:
            return SpecFlowStatus(
                "PROVEN", f"spec_01_{candidate_status}", None, f"owner decision {candidate_status.upper()} is terminal"
            )
        if candidate_status not in {
            "spike_planning_authorized",
            "spike_approval_pending",
            "spike_authorized",
            "spike_running",
            "spike_verdict_recorded",
            "spike_partial_recorded",
            "spike_revisit_eligible",
            "preregistration_authorized",
            "promotion_pending",
        }:
            return SpecFlowStatus(
                "NOT_RUNNABLE", "decide_spec_01", None, "SPEC-01 owner decision did not promote the Candidate"
            )
        if "spec_02_live_run_approval" not in documents:
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "spec_01_promoted",
                "approve_spec_02",
                "separate durable Stephen live-run approval is required",
            )
        if "spec_02_operator_brief" not in documents:
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "approve_spec_02",
                "prepare_spec_02",
                "Codex desktop SPEC-02 brief preparation is required",
            )
        if not {"OR-014", "OR-015", "OR-016", "OR-017"}.issubset(rows):
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "prepare_spec_02",
                "start_spec_02",
                "exact operational lease, attempt, limits, and authority are required",
            )
        if not ({"OR-018", "OR-019"} & rows):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "start_spec_02",
                "return_spec_02",
                "manually produced SPEC-02 evidence is required; no model is launched",
            )
        partial_spike = "OR-019" in rows
        spike_review_rows = {"OR-037", "OR-021"} if partial_spike else {"OR-036", "OR-020"}
        if not spike_review_rows.issubset(rows):
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "return_spec_02",
                "review_spec_02",
                "independent exact-subject SPEC-02 review is required",
            )
        if partial_spike:
            return SpecFlowStatus(
                "PROVEN", "spec_02_partial_reviewed", None, "partial SPEC-02 evidence is an explicit terminal stop"
            )
        if not {"OR-026", "OR-027"}.issubset(rows):
            return SpecFlowStatus(
                "OWNER_BLOCKED", "review_spec_02", "decide_spec_02", "explicit owner terminal decision is required"
            )
        return SpecFlowStatus(
            "PROVEN", "spec_02_owner_decided", None, "candidate evidence is recorded; no scientific claim was published"
        )

    @staticmethod
    def _canonical_packet(path: Path) -> dict[str, Any]:
        try:
            raw = path.resolve(strict=True).read_bytes()
            packet = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigurationError("invalid SPEC action packet") from exc
        if not isinstance(packet, dict) or set(packet) != _PACKET_FIELDS or raw != canonical_bytes(packet):
            raise ConfigurationError("SPEC action packet must be one exact canonical object")
        if (
            packet.get("schema_id") != "ars://portfolio/spec-flow-action"
            or packet.get("schema_version") != "1.0.0"
            or packet.get("route_id") != ROUTE_ID
        ):
            raise ConfigurationError("SPEC action packet route binding differs")
        retry_preimage = {key: deepcopy(value) for key, value in packet.items() if key != "retry_id"}
        expected_retry_id = f"spec-flow:{packet.get('action')}:{sha256_hex(canonical_bytes(retry_preimage))}"
        if packet.get("retry_id") != expected_retry_id:
            raise ConflictError("SPEC action retry identity conflicts with the exact action packet")
        if not isinstance(packet.get("commands"), list):
            raise ConfigurationError("SPEC action packet commands must be an array")
        return packet

    def _validate_commands(
        self,
        action: str,
        commands: list[Any],
        completed_rows: set[str],
    ) -> list[dict[str, Any]]:
        expected = _COMMAND_ACTION_ROWS.get(action, ())
        if len(commands) != (1 if expected else 0):
            raise IntegrityError("SPEC action packet must contain only the exact next route command")
        validated: list[dict[str, Any]] = []
        rows: list[str] = []
        for envelope in commands:
            if (
                not isinstance(envelope, dict)
                or set(envelope)
                != {
                    "command_id",
                    "command_type",
                    "actor_id",
                    "authority_grant_id",
                    "idempotency_key",
                    "target_stream_id",
                    "expected_stream_version",
                    "payload",
                }
                or not isinstance(envelope.get("payload"), dict)
            ):
                raise IntegrityError("SPEC action command is not an object")
            command = Command(deepcopy(envelope))
            binding = self.operator.schemas.command_binding(command.envelope["command_type"])
            if binding is None:
                raise IntegrityError("SPEC action command has no active schema binding")
            routed_row, _route = discovery_route(command)
            declared_row = command.envelope["payload"].get("row_id")
            row = routed_row if declared_row is None else declared_row
            if not isinstance(row, str) or routed_row != row:
                raise IntegrityError("SPEC action command route binding differs")
            rows.append(row)
            if row in {"OR-110", "OR-116"}:
                kind = "dossier_expected_set" if row == "OR-110" else "path_registration"
                supplied_subject = command.envelope["payload"].get("subject")
                exact_subject = build_spec_authority_subject(self.operator.repository_root, kind)
                if not isinstance(supplied_subject, Mapping):
                    raise IntegrityError("SPEC authority registration has no exact subject")
                supplied_core = {
                    key: value
                    for key, value in supplied_subject.items()
                    if key != "subject_sha256" and not key.startswith("authority_file_")
                }
                if supplied_core != exact_subject:
                    raise IntegrityError("SPEC authority registration differs from the proposed route subject")
            validated.append(command.envelope)
        if expected:
            next_rows = [row for row in expected if row not in completed_rows]
            allowed = {next_rows[0]} if next_rows else set()
            allowed.update(row for row in expected if row in completed_rows)
            if rows[0] not in allowed:
                raise IntegrityError("SPEC action command is not the exact next route row")
        return validated

    def _validate_roles(self, commands: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]]) -> None:
        if not commands:
            return
        command = Command(deepcopy(commands[-1]))
        row, _route = discovery_route(command)
        actor = commands[-1].get("actor_id")
        producer = _actor_for_row(events, "OR-004") or _actor_for_row(events, "OR-005")
        reviewer = _actor_for_row(events, "OR-006") or _actor_for_row(events, "OR-007")
        if row in {"OR-006", "OR-007"} and actor == producer:
            raise IntegrityError("SPEC-01 reviewer must be independent of the producer")
        if row == "OR-013" and actor == reviewer:
            raise IntegrityError("SPEC-01 owner decider must be distinct from the reviewer")
        spike_producer = _actor_for_row(events, "OR-018") or _actor_for_row(events, "OR-019")
        spike_reviewer = _actor_for_row(events, "OR-020") or _actor_for_row(events, "OR-021")
        if row in {"OR-020", "OR-021"} and actor == spike_producer:
            raise IntegrityError("SPEC-02 reviewer must be independent of the producer")
        if row == "OR-027" and actor == spike_reviewer:
            raise IntegrityError("SPEC-02 owner decider must be distinct from the reviewer")

    def _register_document(self, action: str, document: Any, registration: Any) -> dict[str, Any]:
        if (
            not isinstance(document, dict)
            or document.get("document_type") != _DOCUMENT_TYPES[action]
            or document.get("route_id") != ROUTE_ID
        ):
            raise IntegrityError("SPEC document type or route binding differs")
        schema_id = _DOCUMENT_ACTION_SCHEMA[action]
        try:
            self.operator.schemas.validate(schema_id, document, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("SPEC document schema rejected the action packet") from exc
        if action.startswith("prepare_spec_"):
            manifest = document.get("brief_manifest")
            if not isinstance(manifest, dict):
                raise IntegrityError("SPEC brief package has no accepted brief manifest")
            try:
                self.operator.schemas.validate("ars://methods/brief-manifest", manifest)
            except SchemaError as exc:
                raise IntegrityError("SPEC brief package is not an accepted brief export") from exc
            if document.get("brief_manifest_sha256") != sha256_hex(canonical_bytes(manifest)):
                raise IntegrityError("SPEC brief package does not bind its exact manifest bytes")
            alias = "SPEC-01" if action == "prepare_spec_01" else "SPEC-02"
            source = next(item for item in self.route["sources"] if item["alias"] == alias)
            route_source = document.get("route_source", {})
            if route_source.get("raw_sha256") != source["sha256"]:
                raise IntegrityError("SPEC brief package does not bind the governed route source")
            expected_blob = _git(
                self.operator.repository_root, "rev-parse", f"HEAD:{route_source.get('relative_path')}"
            )
            if route_source.get("git_blob") != expected_blob:
                raise IntegrityError("SPEC brief package does not bind the committed route source")
        if action.startswith("return_spec_"):
            expected_outcome = "PARTIAL" if action.endswith("_partial") else "COMPLETE"
            if document.get("outcome") != expected_outcome:
                raise IntegrityError("SPEC return outcome differs from the selected route branch")
            response = document.get("responds_to")
            if not isinstance(response, dict):
                raise IntegrityError("SPEC return has no exact brief response binding")
            expected_kind = (
                "spec_01_operator_brief" if action.startswith("return_spec_01") else "spec_02_operator_brief"
            )
            _events, projection, registered = self._snapshot()
            briefs = registered.get(expected_kind, ())
            if len(briefs) != 1:
                raise IntegrityError("SPEC return cannot resolve one registered brief")
            brief = briefs[0]
            if (
                response.get("brief_artefact_id") != brief.get("brief_manifest", {}).get("brief_artefact_id")
                or response.get("brief_manifest_sha256") != brief.get("brief_manifest_sha256")
                or response.get("operator_session_id") != brief.get("operator_session", {}).get("session_id")
            ):
                raise IntegrityError("SPEC return does not bind the registered brief and operator session")
            embedded = document.get("embedded_artefact")
            if not isinstance(embedded, dict):
                raise IntegrityError("SPEC return embedded artefact is missing")
            try:
                self.operator.schemas.validate(
                    embedded.get("schema_id"),
                    embedded,
                    schema_version=embedded.get("schema_version"),
                )
            except SchemaError as exc:
                raise IntegrityError("SPEC return embedded artefact is invalid") from exc
            embedded_sha256 = sha256_hex(canonical_bytes(embedded))
            hashes = {
                item.get("name"): item.get("sha256")
                for item in document.get("artifact_hashes", ())
                if isinstance(item, Mapping)
            }
            if hashes.get("embedded_artefact") != embedded_sha256:
                raise IntegrityError("SPEC return does not bind the embedded artefact hash")
            if action.startswith("return_spec_02") and not {
                "raw_output",
                "source",
                "checks",
                "result",
                "embedded_artefact",
            }.issubset(hashes):
                raise IntegrityError("SPEC-02 return omits a required raw output/source/check/result hash")
        if action == "approve_spec_02":
            events = tuple(self.operator.ledger.iter_events())
            owner_actor = _actor_for_row(events, "OR-013")
            if document.get("owner", {}).get("actor_id") != owner_actor:
                raise IntegrityError("SPEC-02 approval is not the promoting owner")
            source = next(item for item in self.route["sources"] if item["alias"] == "SPEC-02")
            if document.get("spec_02_subject", {}).get("sha256") != source["sha256"]:
                raise IntegrityError("SPEC-02 approval subject differs from the governed source")
            if document.get("brief_identity", {}).get("sha256") != source["sha256"]:
                raise IntegrityError("SPEC-02 approval does not bind the governed brief identity")
            promotion_events = [
                event
                for event in events
                if isinstance(event.get("payload"), Mapping) and event["payload"].get("row_id") == "OR-013"
            ]
            promotion = document.get("spec_01_promotion", {})
            if len(promotion_events) != 1 or (
                promotion.get("id") != promotion_events[0].get("event_id")
                or promotion.get("sha256") != promotion_events[0].get("event_hash")
            ):
                raise IntegrityError("SPEC-02 approval does not bind the exact SPEC-01 promotion")
            try:
                approved = datetime.fromisoformat(document["approved_at"].replace("Z", "+00:00"))
                starts = datetime.fromisoformat(document["valid_window"]["starts_at"].replace("Z", "+00:00"))
                expires = datetime.fromisoformat(document["valid_window"]["expires_at"].replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityError("SPEC-02 approval window is invalid") from exc
            if not starts <= approved < expires:
                raise IntegrityError("SPEC-02 approval is outside its explicit live-run window")
        if (
            not isinstance(registration, dict)
            or set(registration) != _REGISTRATION_FIELDS
            or not isinstance(registration.get("manifest"), dict)
        ):
            raise ConfigurationError("SPEC document registration fields are not exact")
        if registration.get("project_id") != self.operator.ledger.project_id:
            raise IntegrityError("SPEC document registration project differs")
        document_actor = (
            document.get("operator_session", {}).get("operator_actor_id")
            or document.get("producer", {}).get("actor_id")
            or document.get("owner", {}).get("actor_id")
        )
        if registration.get("actor_id") != document_actor:
            raise IntegrityError("SPEC document registration actor differs from its semantic producer")
        service = CommandService(
            self.operator.control_root,
            self.operator.ledger,
            ObjectStore(self.operator.control_root),
            ReceiptStore(self.operator.control_root),
            self.operator.schemas,
            authority_resolver=self.operator.authority_resolver,
            clock=lambda: datetime.now(UTC),
        )
        registered = register_candidate_document(
            value=document,
            registration=CandidateRegistration(**deepcopy(registration)),
            document_store=CandidateDocumentStore(
                self.operator.control_root, relative_directory=Path("methods/documents/spec-flow")
            ),
            command_service=service,
        )
        return {
            "artefact_id": registered.artefact_id,
            "content_sha256": registered.content_sha256,
            "receipt": asdict(registered.receipt),
        }

    def _prepare_spec(self, stage: str, packet: Mapping[str, Any]) -> dict[str, Any]:
        if stage not in {"SPEC-01", "SPEC-02"}:
            raise ValueError("unsupported SPEC preparation stage")
        action = "prepare_spec_01" if stage == "SPEC-01" else "prepare_spec_02"
        route_path = _SPEC_01_PATH if stage == "SPEC-01" else _SPEC_02_PATH
        expected_import_type = "AssayScorecard" if stage == "SPEC-01" else "SpikeVerdict"
        semantic = packet.get("document")
        registrations = packet.get("registration")
        required_semantic = {
            "operator_actor_id",
            "operator_session_id",
            "recipient_id",
            "purpose",
            "scope",
            "evaluation_time",
            "created_at",
            "application_version",
            "handoff_expires_at",
        }
        if not isinstance(semantic, dict) or set(semantic) != required_semantic:
            raise IntegrityError(f"{stage} preparation requires only exact semantic operator inputs")
        if not isinstance(registrations, dict) or set(registrations) != {
            "context_authority_grant_id",
            "brief_registration",
            "package_registration",
        }:
            raise IntegrityError(f"{stage} preparation registration authority is incomplete")
        actor_id = semantic["operator_actor_id"]
        if stage == "SPEC-02":
            _events, _projection, durable_documents = self._snapshot()
            if len(durable_documents.get("spec_02_live_run_approval", ())) != 1:
                raise IntegrityError("SPEC-02 preparation requires one durable live-run approval")
        for key in ("brief_registration", "package_registration"):
            value = registrations[key]
            if not isinstance(value, dict) or set(value) != _REGISTRATION_FIELDS or value.get("actor_id") != actor_id:
                raise IntegrityError(f"{stage} registration actor differs from the operator")
        service = CommandService(
            self.operator.control_root,
            self.operator.ledger,
            ObjectStore(self.operator.control_root),
            ReceiptStore(self.operator.control_root),
            self.operator.schemas,
            authority_resolver=self.operator.authority_resolver,
            governing_evidence_resolver=GoverningScientificReviewStore(
                ObjectStore(self.operator.control_root), self.operator.schemas
            ),
            clock=lambda: datetime.now(UTC),
        )
        compiled, source_resolver = deliver_spec_owner_context(
            operator=self.operator,
            command_service=service,
            actor_id=actor_id,
            authority_grant_id=str(registrations["context_authority_grant_id"]),
            operator_session_id=str(semantic["operator_session_id"]),
            recipient_id=str(semantic["recipient_id"]),
            purpose=str(semantic["purpose"]),
            scope=str(semantic["scope"]),
            retry_identity=str(packet["retry_id"]),
            application_version=str(semantic["application_version"]),
            valid_from=str(semantic["evaluation_time"]),
            expires_at=str(semantic["handoff_expires_at"]),
        )
        _events, projection, _documents = self._snapshot()
        input_states = self._brief_input_states(projection)
        route_source = next(item for item in self.route["sources"] if item["alias"] == stage)
        spec_rows = [
            state
            for state in input_states.values()
            if state["manifest"]["artefact_type"] == "spec_operator_source"
            and state.get("content_sha256") == route_source["sha256"]
        ]
        method_rows = [
            state for state in input_states.values() if state["manifest"]["artefact_type"] == "methods_asset"
        ]
        if len(spec_rows) != 1 or not method_rows:
            raise IntegrityError(f"{stage} accepted brief inputs are not exact")
        methods_pack = load_methods_pack(self.operator.repository_root)
        assets = []
        for state in method_rows:
            manifest = state["manifest"]
            raw = (self.operator.control_root / manifest["relative_path"]).read_bytes()
            matches = [asset for asset in methods_pack.assets if asset.raw_bytes == raw]
            if len(matches) != 1:
                raise IntegrityError("accepted Methods artefact is not an exact current pack asset")
            asset = matches[0]
            assets.append(
                {
                    "artefact_id": manifest["artefact_id"],
                    "content_sha256": state["content_sha256"],
                    "task_id": manifest["task_id"],
                    "asset_id": asset.asset_id,
                    "version": asset.version,
                    "identity": asset.identity,
                    "identity_scheme": asset.identity_scheme,
                }
            )
        spec_state = spec_rows[0]
        spec_manifest = spec_state["manifest"]
        consumers = ArtefactEvidenceConsumers(
            ArtefactUseResolver(
                ledger=self.operator.ledger,
                objects=ObjectStore(self.operator.control_root),
                schemas=self.operator.schemas,
                contract_loader=ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT),
                governing_evidence=GoverningScientificReviewStore(
                    ObjectStore(self.operator.control_root), self.operator.schemas
                ),
                content_reader=ControlRootArtefactContentReader(self.operator.control_root),
                authority_state_validator=self.operator.authority_resolver.validate_replayed_administration_state,
            )
        )
        try:
            evaluation_time = datetime.fromisoformat(str(semantic["evaluation_time"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise IntegrityError("SPEC-01 evaluation time is invalid") from exc
        snapshot = source_resolver.snapshot
        exported = export_brief(
            request={
                "brief_purpose": semantic["purpose"],
                "context": {
                    "context_id": compiled.context_id,
                    "revision": compiled.revision,
                    "packet_sha256": compiled.packet_sha256,
                    "consumer_id": semantic["recipient_id"],
                    "purpose": semantic["purpose"],
                    "scope": semantic["scope"],
                    "evaluation_time": evaluation_time,
                    "control_store_identity": self.operator.ledger.store_identity,
                    "source_position": snapshot.source_position,
                    "source_hash": snapshot.source_hash,
                },
                "created_at": semantic["created_at"],
                "subjects": [
                    {
                        "artefact_id": spec_manifest["artefact_id"],
                        "content_sha256": spec_state["content_sha256"],
                        "task_id": spec_manifest["task_id"],
                        "subject_kind": "spec_operator_source",
                        "path_or_name": spec_manifest["relative_path"],
                        "role": "primary_subject",
                    }
                ],
                "assets": assets,
                "expected_import_types": ["ExploratoryMemo"],
                "deidentification": None,
                "prohibitions": [
                    "no provider or model launch",
                    "no automatic promotion",
                    "import is candidate evidence only",
                ],
                "required_session_fields": ["operator_actor_id", "operator_session_id"],
            },
            context_resolver=resolve_context_packet_for_consumer,
            context_events=lambda: self.operator.ledger.snapshot().events,
            context_objects=ObjectStore(self.operator.control_root),
            context_source_resolver=source_resolver,
            artefact_consumers=consumers,
            methods_pack=methods_pack,
            schema_registry=self.operator.schemas,
            registration=CandidateRegistration(**deepcopy(registrations["brief_registration"])),
            document_store=CandidateDocumentStore(
                self.operator.control_root, relative_directory=Path("methods/documents/spec-flow")
            ),
            command_service=service,
        )
        source = route_source
        package = {
            "schema_id": "ars://portfolio/spec-operator-brief-package",
            "schema_version": "1.0.0",
            "document_type": _DOCUMENT_TYPES[action],
            "route_id": ROUTE_ID,
            "stage": stage,
            "route_expected_return_type": expected_import_type,
            "route_source": {
                "relative_path": route_path.as_posix(),
                "raw_sha256": source["sha256"],
                "git_blob": _git(self.operator.repository_root, "rev-parse", f"HEAD:{route_path.as_posix()}"),
            },
            "brief_manifest": exported.manifest,
            "brief_manifest_sha256": sha256_hex(canonical_bytes(exported.manifest)),
            "operator_session": {
                "session_id": semantic["operator_session_id"],
                "operator_actor_id": actor_id,
                "application": "Codex desktop",
                "application_version": semantic["application_version"],
                "manually_operated": True,
            },
            "prohibitions": [
                "no provider or model launch",
                "no automatic promotion",
                "import is candidate evidence only",
            ],
        }
        result = self._register_document(action, package, registrations["package_registration"])
        return {"registration": result, "context_id": compiled.context_id, "brief": package}

    def advance(self, action: str, packet_path: Path) -> dict[str, Any]:
        packet = self._canonical_packet(packet_path)
        if packet.get("action") != action:
            raise IntegrityError("SPEC action argument and packet differ")
        status = self.status()
        accepted_actions = {status.next_action}
        if status.next_action == "return_spec_01":
            accepted_actions = {"return_spec_01_complete", "return_spec_01_partial"}
        elif status.next_action == "review_spec_01":
            accepted_actions = {"review_spec_01_complete", "review_spec_01_partial"}
        elif status.next_action == "return_spec_02":
            accepted_actions = {"return_spec_02_complete", "return_spec_02_partial"}
        elif status.next_action == "review_spec_02":
            accepted_actions = {"review_spec_02_complete", "review_spec_02_partial"}
        events = tuple(self.operator.ledger.iter_events())
        _events, _projection, documents = self._snapshot()
        completed_rows = set(_rows(events, _projection))
        expected_rows = set(_COMMAND_ACTION_ROWS.get(action, ()))
        expected_document = _DOCUMENT_TYPES.get(action)
        already_completed = bool(
            (not expected_rows or expected_rows.issubset(completed_rows))
            and (expected_document is None or expected_document in documents)
        )
        if action not in accepted_actions and not already_completed:
            raise IntegrityError(f"SPEC action is not next; exact next action is {status.next_action}")
        brief_input_action = action in {
            "register_spec_01_brief_inputs",
            "review_spec_01_brief_inputs",
            "accept_spec_01_brief_inputs",
        }
        commands = [] if brief_input_action else self._validate_commands(action, packet["commands"], completed_rows)
        self._validate_roles(commands, events)
        document_required = action in _DOCUMENT_ACTION_SCHEMA
        if action == "register_spec_01_brief_inputs":
            if packet.get("document") is not None or not isinstance(packet.get("registration"), dict):
                raise IntegrityError("SPEC brief-input registration packet is malformed")
            entries = packet["registration"].get("raw_publications")
            if not isinstance(entries, list) or len(entries) < 2 or packet["commands"]:
                raise IntegrityError("SPEC brief-input registrations are incomplete")
            service = CommandService(
                self.operator.control_root,
                self.operator.ledger,
                ObjectStore(self.operator.control_root),
                ReceiptStore(self.operator.control_root),
                self.operator.schemas,
                authority_resolver=self.operator.authority_resolver,
                clock=lambda: datetime.now(UTC),
            )
            registrations = []
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) != {"publication", "registration"}:
                    raise IntegrityError("SPEC brief-input registration entry is malformed")
                registered = publish_registered_raw_content(
                    repository_root=self.operator.repository_root,
                    publication=RawContentPublication(**entry["publication"]),
                    registration=CandidateRegistration(**entry["registration"]),
                    control_root=self.operator.control_root,
                    command_service=service,
                )
                registrations.append(
                    {"artefact_id": registered.artefact_id, "content_sha256": registered.content_sha256}
                )
            return {
                "route_id": ROUTE_ID,
                "action": action,
                "retry_id": packet["retry_id"],
                "registration": registrations,
                "receipts": [],
                "status": asdict(self.status()),
            }
        if action in {"review_spec_01_brief_inputs", "accept_spec_01_brief_inputs"}:
            review_publications = packet.get("registration")
            if packet.get("document") is not None or (
                action == "accept_spec_01_brief_inputs" and review_publications is not None
            ):
                raise IntegrityError("SPEC brief-input authority action cannot register a document")
            _events, projection, _documents = self._snapshot()
            inputs = self._brief_input_states(projection)
            expected_type = "RecordScientificReview" if action.startswith("review_") else "SetArtefactUseAuthority"
            if len(packet["commands"]) != len(inputs):
                raise IntegrityError("SPEC brief-input authority commands are incomplete")
            review_store = GoverningScientificReviewStore(
                ObjectStore(self.operator.control_root), self.operator.schemas
            )
            if action == "review_spec_01_brief_inputs":
                if (
                    not isinstance(review_publications, dict)
                    or set(review_publications) != {"governing_reviews"}
                    or not isinstance(review_publications["governing_reviews"], list)
                    or len(review_publications["governing_reviews"]) != len(inputs)
                ):
                    raise IntegrityError("SPEC brief-input governing reviews are incomplete")
                publications = review_publications["governing_reviews"]
            else:
                publications = []
            service = CommandService(
                self.operator.control_root,
                self.operator.ledger,
                ObjectStore(self.operator.control_root),
                ReceiptStore(self.operator.control_root),
                self.operator.schemas,
                authority_resolver=self.operator.authority_resolver,
                governing_evidence_resolver=review_store,
                clock=lambda: datetime.now(UTC),
            )
            receipts = []
            for index, envelope in enumerate(packet["commands"]):
                target = envelope.get("target_stream_id") if isinstance(envelope, dict) else None
                state = inputs.get(str(target))
                payload = envelope.get("payload") if isinstance(envelope, dict) else None
                if (
                    state is None
                    or envelope.get("command_type") != expected_type
                    or not isinstance(payload, dict)
                    or payload.get("artefact_id") != target
                    or payload.get("subject_sha256") != state.get("content_sha256")
                ):
                    raise IntegrityError("SPEC brief-input authority command subject differs")
                if expected_type == "RecordScientificReview" and envelope.get("actor_id") == state.get(
                    "manifest", {}
                ).get("producer_actor_id"):
                    raise IntegrityError("SPEC brief-input reviewer must be independent of the producer")
                if expected_type == "RecordScientificReview":
                    publication = publications[index]
                    evidence_refs = payload.get("evidence_refs")
                    if (
                        not isinstance(publication, dict)
                        or set(publication) != {"reference_id", "record"}
                        or not isinstance(evidence_refs, list)
                        or evidence_refs != [publication.get("reference_id")]
                        or not isinstance(publication.get("record"), dict)
                        or publication["record"].get("subject_sha256") != state.get("content_sha256")
                        or publication["record"].get("reviewer_actor_id") != envelope.get("actor_id")
                    ):
                        raise IntegrityError("SPEC brief-input governing review binding differs")
                    review_store.publish(publication["reference_id"], publication["record"])
                receipts.append(asdict(service.submit(deepcopy(envelope))))
            return {
                "route_id": ROUTE_ID,
                "action": action,
                "retry_id": packet["retry_id"],
                "registration": None,
                "receipts": receipts,
                "status": asdict(self.status()),
            }
        if action in {"prepare_spec_01", "prepare_spec_02"}:
            if packet["commands"]:
                raise IntegrityError("SPEC preparation cannot submit a Discovery route command")
            prepared = self._prepare_spec("SPEC-01" if action == "prepare_spec_01" else "SPEC-02", packet)
            return {
                "route_id": ROUTE_ID,
                "action": action,
                "retry_id": packet["retry_id"],
                **prepared,
                "receipts": [],
                "status": asdict(self.status()),
            }
        if document_required != (packet.get("document") is not None and packet.get("registration") is not None):
            raise IntegrityError("SPEC action document/registration presence differs")
        if not document_required and (packet.get("document") is not None or packet.get("registration") is not None):
            raise IntegrityError("SPEC command-only action cannot register a document")
        registration_result = None
        if document_required:
            registration_result = self._register_document(action, packet["document"], packet["registration"])
        receipts = [asdict(self.operator.submit(command)) for command in commands]
        return {
            "route_id": ROUTE_ID,
            "action": action,
            "retry_id": packet["retry_id"],
            "registration": registration_result,
            "receipts": receipts,
            "status": asdict(self.status()),
        }


__all__ = ["ROUTE_ID", "SpecFlow", "SpecFlowStatus", "build_spec_authority_subject"]
