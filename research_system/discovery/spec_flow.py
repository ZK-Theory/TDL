"""Provider-free operator coordinator for the governed Gate 6 SPEC route.

The coordinator owns no research execution and no second lifecycle state
machine.  Durable lifecycle truth is replayed from the Discovery ledger; an
advance packet merely supplies the real identities, authority references, and
evidence required by the one next route action.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
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
from research_system.authority import GrantedCommandIdentity
from research_system.context.registry import resolve_context_packet_for_consumer
from research_system.context.spec_bridge import deliver_spec_owner_context, derive_spec_owner_context_id
from research_system.discovery.operator import DiscoveryOperator
from research_system.discovery.path_safety import read_contained_regular_file
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierMember,
    accepted_expected_set_hash,
)
from research_system.discovery.authority import (
    PORTABLE_SPEC_REQUIRED_MEMBERS,
    validate_portable_path_subject,
)
from research_system.discovery.rules import _is_spec_route_candidate
from research_system.discovery.routes import discovery_route
from research_system.discovery.runtime import DiscoveryRuntime, _spec_02_return_evidence_matches
from research_system.discovery.spec_action_journal import (
    ACTION_IDENTITY_DIRECTORY as _SPEC_ACTION_IDENTITY_DIRECTORY,
    JOURNAL_DIRECTORY as _SPEC_ACTION_JOURNAL_DIRECTORY,
    PACKET_FIELDS as _PACKET_FIELDS,
    RECOVERABLE_ACTIONS as _RECOVERABLE_ACTIONS,
    ROUTE_ID,
    pending_preparation as _pending_action_preparation,
    preparation_value as _action_preparation_value,
    read_action_identity as _read_action_identity,
    read_preparation as _prepared_action_journal,
)
from research_system.discovery.source_correction import (
    resolve_remote_tag as _resolve_remote_tag,
    verify_remote_commit_paths as _verify_remote_commit_paths,
    verify_source_correction_remote as _verify_source_correction_remote,
)
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system.git_execution import run_git
from research_system.git_provenance import read_exact_committed_physical_file
from research_system.ids import new_id
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    RawContentPublication,
    prepare_candidate_document,
    prepare_registered_raw_content,
    publish_registered_raw_content,
    recover_registered_content,
    register_candidate_document,
    spec_brief_input_artefact_id,
)
from research_system.evidence.consumers import ArtefactEvidenceConsumers
from research_system.methods.brief import export_brief
from research_system.methods.pack import load_methods_pack
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from research_system.store.ledger import EventLedger, _issue_validated_service_session
from research_system.store.spec_preparation_fence import SpecPreparationFence


_ROUTE_PATH = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
_SPEC_01_PATH = _ROUTE_PATH.parent / "spec-01-assay-brief-v1.1.0.md"
_SPEC_02_PATH = _ROUTE_PATH.parent / "spec-02-micro-spike-contract-v1.1.0.md"
_DOSSIER_AUTHORITY_PATH = _ROUTE_PATH.parent / "spec-dossier-expected-set-authority.json"
_PATH_AUTHORITY_PATH = _ROUTE_PATH.parent / "spec-path-registration-authority.json"
_DOSSIER_MANIFEST_PATH = _ROUTE_PATH.parent / "spec-research-dossier-manifest.json"
_REGISTERED_PATH_POLICY_PATH = _ROUTE_PATH.parent / "registered-path-read-policy.json"
_P042_DECISION_PATH = Path("docs/plans/agentic-research-system/03-decisions-and-open-questions.md")
_P042_HEADING = b"### P-042 - Owner-operated external model sessions"
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


@dataclass(frozen=True)
class SpecFlowStatus:
    capability_state: str
    completed_stage: str
    next_action: str | None
    block_reason: str | None
    route_id: str = ROUTE_ID


@dataclass(frozen=True)
class _SpecActionDefinition:
    """One declarative completion contract for a public SPEC action."""

    action: str
    next_action: str
    required_rows: tuple[str, ...] = ()
    document_type: str | None = None
    document_schema: str | None = None
    single_shot: bool = False
    brief_input_state: str | None = None


@dataclass(frozen=True)
class _SpecActionState:
    """One evaluated action phase derived from durable route evidence."""

    definition: _SpecActionDefinition
    phase: str
    effects_complete: bool
    completion_sealed: bool


_ACTION_DEFINITION_ROWS = (
    _SpecActionDefinition("bootstrap_genesis", "bootstrap_genesis", ("OR-140",)),
    _SpecActionDefinition(
        "bootstrap_assay_authority",
        "bootstrap_assay_authority",
        tuple(f"OR-{value:03d}" for value in range(101, 109)),
    ),
    _SpecActionDefinition(
        "bootstrap_dossier_authority",
        "bootstrap_dossier_authority",
        tuple(f"OR-{value:03d}" for value in range(110, 116)),
    ),
    _SpecActionDefinition(
        "bootstrap_path_authority",
        "bootstrap_path_authority",
        tuple(f"OR-{value:03d}" for value in range(116, 122)),
    ),
    _SpecActionDefinition("admit_dossier", "admit_dossier", ("OR-028",)),
    _SpecActionDefinition("observe_source", "observe_source", ("OR-029",)),
    _SpecActionDefinition("request_spec_01", "request_spec_01", ("OR-003",)),
    _SpecActionDefinition(
        "register_spec_01_brief_inputs",
        "register_spec_01_brief_inputs",
        single_shot=True,
        brief_input_state="registered",
    ),
    _SpecActionDefinition(
        "review_spec_01_brief_inputs",
        "review_spec_01_brief_inputs",
        single_shot=True,
        brief_input_state="reviewed",
    ),
    _SpecActionDefinition(
        "accept_spec_01_brief_inputs",
        "accept_spec_01_brief_inputs",
        single_shot=True,
        brief_input_state="accepted",
    ),
    _SpecActionDefinition(
        "prepare_spec_01",
        "prepare_spec_01",
        document_type="spec_01_operator_brief",
        document_schema="ars://portfolio/spec-operator-brief-package",
        single_shot=True,
    ),
    _SpecActionDefinition(
        "return_spec_01_complete",
        "return_spec_01",
        required_rows=("OR-004",),
        document_type="spec_01_return",
        document_schema="ars://portfolio/spec-operator-return",
        single_shot=True,
    ),
    _SpecActionDefinition(
        "return_spec_01_partial",
        "return_spec_01",
        required_rows=("OR-005",),
        document_type="spec_01_return",
        document_schema="ars://portfolio/spec-operator-return",
        single_shot=True,
    ),
    _SpecActionDefinition("review_spec_01_complete", "review_spec_01", ("OR-034", "OR-006")),
    _SpecActionDefinition("review_spec_01_partial", "review_spec_01", ("OR-035", "OR-007")),
    _SpecActionDefinition("decide_spec_01", "decide_spec_01", ("OR-012", "OR-013")),
    _SpecActionDefinition(
        "correct_spec_01_source",
        "correct_spec_01_source",
        document_type="spec_01_source_correction",
        document_schema="ars://portfolio/spec-01-source-correction",
        single_shot=True,
    ),
    _SpecActionDefinition(
        "approve_spec_02",
        "approve_spec_02",
        document_type="spec_02_live_run_approval",
        document_schema="ars://portfolio/spec-02-live-run-approval",
        single_shot=True,
    ),
    _SpecActionDefinition(
        "prepare_spec_02",
        "prepare_spec_02",
        document_type="spec_02_operator_brief",
        document_schema="ars://portfolio/spec-operator-brief-package",
        single_shot=True,
    ),
    _SpecActionDefinition("start_spec_02", "start_spec_02", ("OR-014", "OR-015", "OR-016", "OR-017")),
    _SpecActionDefinition(
        "return_spec_02_complete",
        "return_spec_02",
        required_rows=("OR-018",),
        document_type="spec_02_return",
        document_schema="ars://portfolio/spec-operator-return",
        single_shot=True,
    ),
    _SpecActionDefinition(
        "return_spec_02_partial",
        "return_spec_02",
        required_rows=("OR-019",),
        document_type="spec_02_return",
        document_schema="ars://portfolio/spec-operator-return",
        single_shot=True,
    ),
    _SpecActionDefinition("review_spec_02_complete", "review_spec_02", ("OR-036", "OR-020")),
    _SpecActionDefinition("review_spec_02_partial", "review_spec_02", ("OR-037", "OR-021")),
    _SpecActionDefinition("decide_spec_02", "decide_spec_02", ("OR-026", "OR-027")),
)
_ACTION_DEFINITIONS = MappingProxyType({definition.action: definition for definition in _ACTION_DEFINITION_ROWS})
if len(_ACTION_DEFINITIONS) != len(_ACTION_DEFINITION_ROWS):  # pragma: no cover - import-time architecture fence
    raise RuntimeError("SPEC action definitions contain a duplicate action")
if any(
    not definition.action
    or not definition.next_action
    or not (definition.required_rows or definition.document_type or definition.brief_input_state)
    or (definition.document_type is None) != (definition.document_schema is None)
    or (definition.document_type is not None and not definition.single_shot)
    or (definition.brief_input_state is not None and not definition.single_shot)
    or len(set(definition.required_rows)) != len(definition.required_rows)
    for definition in _ACTION_DEFINITIONS.values()
):  # pragma: no cover - import-time architecture fence
    raise RuntimeError("SPEC action definition is invalid")
if {definition.action for definition in _ACTION_DEFINITIONS.values() if definition.single_shot} != set(
    _RECOVERABLE_ACTIONS
):  # pragma: no cover - import-time architecture fence
    raise RuntimeError("SPEC action registry and recovery journal differ")

_INITIAL_ACTION_SEQUENCE = (
    "bootstrap_genesis",
    "bootstrap_assay_authority",
    "bootstrap_dossier_authority",
    "bootstrap_path_authority",
    "admit_dossier",
    "observe_source",
    "request_spec_01",
)
_DOCUMENT_SCHEMA_BY_TYPE: dict[str, str] = {}
for _definition in _ACTION_DEFINITIONS.values():
    if _definition.document_type is None or _definition.document_schema is None:
        continue
    _prior_schema = _DOCUMENT_SCHEMA_BY_TYPE.setdefault(_definition.document_type, _definition.document_schema)
    if _prior_schema != _definition.document_schema:  # pragma: no cover - import-time architecture fence
        raise RuntimeError(f"SPEC document type {_definition.document_type} has conflicting schemas")
_DOCUMENT_ACTIONS_BY_TYPE = MappingProxyType(
    {
        document_type: tuple(
            definition.action
            for definition in _ACTION_DEFINITIONS.values()
            if definition.document_type == document_type
        )
        for document_type in _DOCUMENT_SCHEMA_BY_TYPE
    }
)
_BRIEF_INPUT_TYPES = {"spec_operator_source", "methods_asset"}
_BRIEF_INPUT_SOURCE_TYPES = {
    _SPEC_01_PATH.as_posix(): "spec_operator_source",
    _SPEC_02_PATH.as_posix(): "spec_operator_source",
    ".research-system/methods/assets/adversarial-review-protocol.md": "methods_asset",
}
_BRIEF_INPUT_DESTINATION_PREFIX = "methods/content/spec-flow/"
_SPEC_02_APPROVAL_AUTHORITY_REASON = "Authorize exact governed publication of the owner-approved SPEC-02 run decision."
_SPEC_02_APPROVAL_EVIDENCE_PREFIX = "spec-02-approval-sha256:"


def _git(repository_root: Path, *arguments: str) -> str:
    result = run_git(
        repository_root,
        *arguments,
        unavailable_message="SPEC route Git validation is unavailable",
    )
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
        raw = read_exact_committed_physical_file(
            repository_root,
            authority_path,
            label=f"proposed SPEC {authority_kind} authority",
        )
        subject = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, IntegrityError) as exc:
        raise ConfigurationError("proposed SPEC authority is not an exact committed physical file") from exc
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
                "git_blob": _git(repository_root, "hash-object", "--", relative_path),
            }
        )
    if subject.get("required_member_bindings") != expected_bindings:
        raise ConfigurationError("proposed SPEC portable member set differs from exact route bytes")
    return subject


def validate_spec_route_contract(
    repository_root: Path,
    catalogue_path: Path,
    schemas: Any,
    route: Mapping[str, Any],
) -> None:
    """Validate the closed semantics consumed by the public SPEC coordinator."""

    if not isinstance(route, dict) or route.get("route_id") != ROUTE_ID:
        raise ConfigurationError("SPEC route package is not the exact governed route")
    try:
        schemas.validate("ars://contracts/wp6-6/spec-gate6-route", route, schema_version="1.0.0")
    except SchemaError as exc:
        raise ConfigurationError("SPEC route package schema binding differs") from exc
    if route.get("activation_status") != "inert_proposed" or route.get("authority_activation") != "forbidden":
        raise ConfigurationError("SPEC route package is not inert")
    try:
        catalogue = json.loads(catalogue_path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("SPEC route catalogue is unavailable") from exc
    catalogue_rows = {
        row.get("owner_row_id"): row
        for row in catalogue.get("owner_contract_rows", ())
        if isinstance(row, Mapping) and isinstance(row.get("owner_row_id"), str)
    }
    route_steps = route.get("route_steps")
    exclusions = route.get("intentional_exclusions")
    if not isinstance(route_steps, list) or not isinstance(exclusions, list):
        raise ConfigurationError("SPEC route row partition is malformed")
    route_rows = [row for step in route_steps if isinstance(step, Mapping) for row in step.get("owner_rows", ())]
    excluded_rows = [row for group in exclusions if isinstance(group, Mapping) for row in group.get("owner_rows", ())]
    if (
        not all(isinstance(row, str) and row in catalogue_rows for row in (*route_rows, *excluded_rows))
        or len(route_rows) != len(set(route_rows))
        or len(excluded_rows) != len(set(excluded_rows))
        or set(route_rows) & set(excluded_rows)
        or set(route_rows) | set(excluded_rows) != set(catalogue_rows)
    ):
        raise ConfigurationError("SPEC route row partition differs from the accepted catalogue")
    governed_commands: list[str] = []
    for row_id in route_rows:
        command_type = catalogue_rows[row_id].get("command_type")
        if not isinstance(command_type, str):
            raise ConfigurationError("SPEC route catalogue command is invalid")
        if command_type not in governed_commands:
            governed_commands.append(command_type)
    if route.get("governed_command_types") != governed_commands:
        raise ConfigurationError("SPEC route command derivation differs from the accepted catalogue")
    stage_order = route.get("stage_order")
    if not isinstance(stage_order, list) or len(stage_order) != len(set(stage_order)):
        raise ConfigurationError("SPEC route stage order is invalid")
    stage_positions = {stage: index for index, stage in enumerate(stage_order)}
    try:
        positions = [stage_positions[step["stage"]] for step in route_steps]
    except (KeyError, TypeError) as exc:
        raise ConfigurationError("SPEC route stage binding is invalid") from exc
    if positions != sorted(positions):
        raise ConfigurationError("SPEC route steps are out of order")
    policy_source = f"repo:{_REGISTERED_PATH_POLICY_PATH.as_posix()}"
    if policy_source not in route.get("governing_sources", ()):
        raise ConfigurationError("SPEC route omits its registered-path read policy")
    try:
        policy_raw = (repository_root / _REGISTERED_PATH_POLICY_PATH).read_bytes()
        policy = json.loads(policy_raw)
        schemas.validate(
            "ars://contracts/wp6-6/registered-path-read-policy",
            policy,
            schema_version="1.0.0",
        )
        manifest = json.loads((repository_root / _DOSSIER_MANIFEST_PATH).read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError) as exc:
        raise ConfigurationError("SPEC route registered-path read policy is invalid") from exc
    dependencies = manifest.get("source_dependencies") if isinstance(manifest, Mapping) else None
    if not isinstance(dependencies, list) or len(dependencies) != 1:
        raise ConfigurationError("SPEC route dossier source policy binding is invalid")
    policy_ref = dependencies[0]
    if policy_ref.get("independent_resolution_policy_id") != policy.get("policy_id") or policy_ref.get(
        "independent_resolution_policy_hash"
    ) != sha256_hex(policy_raw):
        raise ConfigurationError("SPEC route dossier source policy hash differs")
    try:
        decisions_raw = (repository_root / _P042_DECISION_PATH).read_bytes()
        decision_start = decisions_raw.index(_P042_HEADING)
        decision_end = decisions_raw.find(b"\n### P-", decision_start + len(_P042_HEADING))
    except (OSError, ValueError) as exc:
        raise ConfigurationError("SPEC route P-042 decision authority is unavailable") from exc
    if decision_end < 0:
        decision_end = len(decisions_raw)
    else:
        decision_end += 1
    if manifest.get("governing_decisions") != [
        {
            "id": "decision:P-042",
            "record_revision": 1,
            "content_hash": sha256_hex(decisions_raw[decision_start:decision_end]),
        }
    ]:
        raise ConfigurationError("SPEC route P-042 decision content binding differs")
    sources = {item.get("alias"): item for item in route.get("sources", ()) if isinstance(item, dict)}
    for alias, relative in (("SPEC-01", _SPEC_01_PATH), ("SPEC-02", _SPEC_02_PATH)):
        source = sources.get(alias)
        try:
            data = (repository_root / relative).read_bytes()
        except OSError as exc:
            raise ConfigurationError(f"{alias} governed source is unavailable") from exc
        if source is None or source.get("size_bytes") != len(data) or source.get("sha256") != sha256_hex(data):
            raise ConfigurationError(f"{alias} governed source binding differs")


def _validate_route(operator: DiscoveryOperator) -> dict[str, Any]:
    route_path = operator.repository_root / _ROUTE_PATH
    try:
        raw = route_path.read_bytes()
        route = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("SPEC route package is unavailable") from exc
    validate_spec_route_contract(operator.repository_root, operator.catalogue_path, operator.schemas, route)
    for relative in (_ROUTE_PATH, _SPEC_01_PATH, _SPEC_02_PATH, _REGISTERED_PATH_POLICY_PATH):
        working_blob = _git(operator.repository_root, "hash-object", "--", relative.as_posix())
        committed_blob = _git(operator.repository_root, "rev-parse", f"HEAD:{relative.as_posix()}")
        if working_blob != committed_blob:
            raise ConfigurationError("SPEC route source is not committed at operator HEAD")
    return route


@dataclass(frozen=True)
class _SpecRouteCensus:
    """One route-subject projection of shared-ledger lifecycle facts."""

    rows: tuple[str, ...]
    actors: Mapping[str, frozenset[str]]
    candidate_ids: frozenset[str]
    events: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_snapshot(
        cls,
        events: Sequence[Mapping[str, Any]],
        projection: Mapping[str, Any],
        *,
        dossier_id: str | None,
    ) -> "_SpecRouteCensus":
        """Census only the exact SPEC dossier and its classified Candidate lineage."""

        def records(name: str) -> Mapping[str, Any]:
            value = projection.get(name)
            return value if isinstance(value, Mapping) else {}

        candidates = records("candidates")
        candidate_ids = {
            candidate_id
            for candidate_id, candidate in candidates.items()
            if isinstance(candidate_id, str)
            and isinstance(candidate, Mapping)
            and _is_spec_route_candidate(projection, candidate)
        }
        entity_ids = set(candidate_ids)
        linked_fields = ("assay_id", "spike_id", "decision_id", "review_id")
        changed = True
        while changed:
            changed = False
            for candidate_id in candidate_ids:
                candidate = candidates.get(candidate_id)
                if not isinstance(candidate, Mapping):
                    continue
                for field in linked_fields:
                    value = candidate.get(field)
                    if isinstance(value, str) and value not in entity_ids:
                        entity_ids.add(value)
                        changed = True
            for name in ("assays", "spikes", "decisions", "reviews"):
                for identity, record in records(name).items():
                    if not isinstance(identity, str) or not isinstance(record, Mapping):
                        continue
                    if identity not in entity_ids and record.get("candidate_id") not in candidate_ids:
                        continue
                    if identity not in entity_ids:
                        entity_ids.add(identity)
                        changed = True
                    for field in linked_fields:
                        value = record.get(field)
                        if isinstance(value, str) and value not in entity_ids:
                            entity_ids.add(value)
                            changed = True

        ordered: list[str] = []
        actors: dict[str, set[str]] = {}
        route_events: list[Mapping[str, Any]] = []

        def is_route_event(event: Mapping[str, Any], payload: Mapping[str, Any], row: str) -> bool:
            if row == "OR-140":
                return event.get("event_type") == "W11CatalogueGenesisImported"
            if event.get("stream_id") in entity_ids:
                return True
            if isinstance(dossier_id, str) and (
                event.get("stream_id") == dossier_id or payload.get("dossier_id") == dossier_id
            ):
                return True
            if any(
                payload.get(field) in entity_ids
                for field in ("candidate_id", "assay_id", "spike_id", "decision_id", "review_id")
            ):
                return True
            blueprints = payload.get("candidate_blueprints")
            return isinstance(blueprints, list) and any(
                isinstance(blueprint, Mapping) and blueprint.get("candidate_id") in candidate_ids
                for blueprint in blueprints
            )

        for event in events:
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                continue
            row = payload.get("row_id") or payload.get("owner_row_id")
            if not isinstance(row, str) or not is_route_event(event, payload, row):
                continue
            if row not in ordered:
                ordered.append(row)
            route_events.append(event)
            actor_id = event.get("actor_id")
            if isinstance(actor_id, str):
                actors.setdefault(row, set()).add(actor_id)
        if isinstance(dossier_id, str) and dossier_id in records("dossiers") and "OR-028" not in ordered:
            ordered.append("OR-028")
        assay_authority = projection.get("assay_bar_authority")
        if isinstance(assay_authority, Mapping):
            contents = assay_authority.get("contents")
            if isinstance(contents, Mapping):
                for content_kind, row in (("rubric", "OR-101"), ("scope", "OR-102")):
                    if isinstance(contents.get(content_kind), Mapping) and row not in ordered:
                        ordered.append(row)
            observations = assay_authority.get("observations")
            if isinstance(observations, Mapping):
                for content_kind, row in (("rubric", "OR-103"), ("scope", "OR-104")):
                    if isinstance(observations.get(content_kind), Mapping) and row not in ordered:
                        ordered.append(row)
            status = assay_authority.get("status")
            inferred_assay_rows = {
                "review_requested": ("OR-105",),
                "reviewed": ("OR-105", "OR-106"),
                "decision_proposed": ("OR-105", "OR-106", "OR-107"),
                "accepted": tuple(f"OR-{value:03d}" for value in range(101, 109)),
            }.get(status, ())
            ordered.extend(row for row in inferred_assay_rows if row not in ordered)
        authorities = projection.get("authorities")
        if isinstance(authorities, Mapping):
            for kind, start in (("dossier_expected_set", 110), ("path_registration", 116)):
                authority = authorities.get(kind)
                if not isinstance(authority, Mapping):
                    continue
                completed_count = {
                    "registered": 1,
                    "observed": 2,
                    "review_requested": 3,
                    "reviewed": 4,
                    "decision_proposed": 5,
                    "accepted": 6,
                }.get(authority.get("status"), 0)
                ordered.extend(
                    row
                    for row in (f"OR-{value:03d}" for value in range(start, start + completed_count))
                    if row not in ordered
                )
        return cls(
            tuple(ordered),
            {row: frozenset(value) for row, value in actors.items()},
            frozenset(candidate_ids),
            tuple(route_events),
        )

    def actor_for_row(self, row: str) -> str | None:
        actors = self.actors.get(row, frozenset())
        if len(actors) > 1:
            raise IntegrityError(f"multiple actors are bound to route row {row}")
        return next(iter(actors)) if actors else None


def _rows(
    events: Sequence[Mapping[str, Any]], projection: Mapping[str, Any], *, dossier_id: str | None = None
) -> tuple[str, ...]:
    return _SpecRouteCensus.from_snapshot(events, projection, dossier_id=dossier_id).rows


@dataclass(frozen=True)
class _RegisteredSpecDocument:
    document_type: str
    artefact_id: str
    content_sha256: str
    registration_event: Mapping[str, Any]
    value: Mapping[str, Any]


@dataclass(frozen=True)
class _RegisteredSpecDocumentIdentity:
    document_type: str
    artefact_id: str
    content_sha256: str
    relative_path: str
    registration_event: Mapping[str, Any]

    @property
    def completion_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.document_type,
            self.artefact_id,
            self.content_sha256,
            str(self.registration_event.get("event_id")),
            str(self.registration_event.get("event_hash")),
        )


def _event_position(event: Mapping[str, Any]) -> int:
    value = event.get("global_position")
    return value if isinstance(value, int) else -1


def _legacy_return_was_consumed(
    route_events: Sequence[Mapping[str, Any]],
    record: _RegisteredSpecDocument,
    *,
    action: str,
) -> bool:
    """Bind one historical return to the exact route payload that consumed it."""

    embedded = record.value.get("embedded_artefact")
    if not isinstance(embedded, Mapping):
        return False
    embedded_sha256 = sha256_hex(canonical_bytes(embedded))
    if action.startswith("return_spec_01"):
        row = "OR-004" if action.endswith("_complete") else "OR-005"
        artifact_key = "scorecard_artifact" if row == "OR-004" else "partial_artifact"
        hash_key = "scorecard_sha256" if row == "OR-004" else "partial_sha256"
    else:
        row = "OR-018" if action.endswith("_complete") else "OR-019"
        artifact_key = "verdict_artifact"
        hash_key = "verdict_sha256"
    return any(
        _event_position(event) > _event_position(record.registration_event)
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("row_id") == row
        and event["payload"].get(artifact_key) == embedded
        and event["payload"].get(hash_key) == embedded_sha256
        and (
            not action.startswith("return_spec_02")
            or event["payload"].get("evidence_refs") == [f"artefact:{record.artefact_id}"]
        )
        for event in route_events
    )


def _legacy_brief_was_consumed(
    events: Sequence[Mapping[str, Any]],
    route_events: Sequence[Mapping[str, Any]],
    records: Sequence[_RegisteredSpecDocument],
    record: _RegisteredSpecDocument,
    *,
    action: str,
) -> bool:
    """Bind one historical brief package through its manifest and exact return/plan."""

    brief_manifest = record.value.get("brief_manifest")
    operator_session = record.value.get("operator_session")
    if not isinstance(brief_manifest, Mapping) or not isinstance(operator_session, Mapping):
        return False
    brief_id = brief_manifest.get("brief_artefact_id")
    brief_sha256 = record.value.get("brief_manifest_sha256")
    manifest_events = [
        event
        for event in events
        if event.get("event_type") == "ArtefactRegistered"
        and event.get("stream_id") == brief_id
        and event.get("payload", {}).get("manifest", {}).get("content_sha256") == brief_sha256
        and _event_position(event) < _event_position(record.registration_event)
    ]
    if len(manifest_events) != 1:
        return False
    if action == "prepare_spec_02":
        source_sha256 = record.value.get("route_source", {}).get("raw_sha256")
        source_path = record.value.get("route_source", {}).get("relative_path")
        approvals = [
            candidate
            for candidate in records
            if candidate.document_type == "spec_02_live_run_approval"
            and _event_position(candidate.registration_event) < _event_position(record.registration_event)
            and candidate.value.get("brief_identity") == {"id": source_path, "sha256": source_sha256}
            and candidate.value.get("spec_02_subject") == {"id": "SPEC-02", "sha256": source_sha256}
        ]
        if len(approvals) != 1:
            return False
        return any(
            _event_position(event) > _event_position(record.registration_event)
            and event.get("event_type") == "SpikePlanned"
            and event.get("payload", {}).get("row_id") == "OR-014"
            and any(
                contract in event.get("payload", {}).get("plan_artifact", {}).get("planned_contracts", ())
                for contract in (f"SPEC-02:{source_sha256}", "SPEC-02:v1.1.0")
            )
            for event in route_events
        )
    expected_response = {
        "brief_artefact_id": brief_id,
        "brief_manifest_sha256": brief_sha256,
        "operator_session_id": operator_session.get("session_id"),
    }
    return any(
        candidate.document_type == "spec_01_return"
        and _event_position(candidate.registration_event) > _event_position(record.registration_event)
        and candidate.value.get("responds_to") == expected_response
        and any(
            _legacy_return_was_consumed(route_events, candidate, action=return_action)
            for return_action in _DOCUMENT_ACTIONS_BY_TYPE["spec_01_return"]
        )
        for candidate in records
    )


def _legacy_spec_02_authority_was_consumed(
    route_events: Sequence[Mapping[str, Any]],
    records: Sequence[_RegisteredSpecDocument],
    record: _RegisteredSpecDocument,
    *,
    action: str,
) -> bool:
    """Bind historical approval/correction bytes to the exact validated OR-014 plan."""

    later_plans = [
        event
        for event in route_events
        if _event_position(event) > _event_position(record.registration_event)
        and event.get("event_type") == "SpikePlanned"
        and event.get("payload", {}).get("row_id") == "OR-014"
    ]
    if len(later_plans) != 1:
        return False
    plan = later_plans[0].get("payload", {}).get("plan_artifact", {})
    if not isinstance(plan, Mapping):
        return False
    if action == "correct_spec_01_source":
        promotion = [
            event
            for event in route_events
            if event.get("payload", {}).get("row_id") == "OR-013"
            and _event_position(event) < _event_position(record.registration_event)
        ]
        return bool(
            len(promotion) == 1
            and record.value.get("decision_ref")
            == {"id": promotion[0].get("event_id"), "sha256": promotion[0].get("event_hash")}
            and record.value.get("scorecard_ref")
            == {
                "id": plan.get("originating_assay_ref", {}).get("id"),
                "sha256": plan.get("originating_assay_ref", {}).get("content_hash"),
            }
        )
    corrections = [candidate for candidate in records if candidate.document_type == "spec_01_source_correction"]
    if len(corrections) > 1:
        return False
    correction = corrections[0] if corrections else None
    promotion = [
        event
        for event in route_events
        if event.get("payload", {}).get("row_id") == "OR-013"
        and _event_position(event) < _event_position(record.registration_event)
    ]
    if len(promotion) != 1 or record.value.get("spec_01_promotion") != {
        "id": promotion[0].get("event_id"),
        "sha256": promotion[0].get("event_hash"),
    }:
        return False
    if correction is None:
        return record.value.get("entry_mode") == "standard_promotion" and record.value.get("source_correction") is None
    return record.value.get("source_correction") == {
        "id": correction.value.get("correction_id"),
        "sha256": correction.content_sha256,
    }


def _legacy_document_was_consumed(
    events: Sequence[Mapping[str, Any]],
    projection: Mapping[str, Any],
    records: Sequence[_RegisteredSpecDocument],
    record: _RegisteredSpecDocument,
    *,
    action: str,
) -> bool:
    """Recognize historical documents only through their exact SPEC consumer relation."""

    route_events = _SpecRouteCensus.from_snapshot(events, projection, dossier_id=None).events
    if action.startswith("return_spec_"):
        return _legacy_return_was_consumed(route_events, record, action=action)
    if action.startswith("prepare_spec_"):
        return _legacy_brief_was_consumed(events, route_events, records, record, action=action)
    return _legacy_spec_02_authority_was_consumed(route_events, records, record, action=action)


def _registered_documents(
    operator: DiscoveryOperator,
    events: Sequence[Mapping[str, Any]],
    projection: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    identities: list[_RegisteredSpecDocumentIdentity] = []
    artefact_streams = projection.get("artefact_streams", {})
    if not isinstance(artefact_streams, Mapping):
        raise IntegrityError("registered SPEC document projection is invalid")
    for stream in artefact_streams.values():
        if not isinstance(stream, Mapping):
            continue
        manifest = stream.get("manifest")
        if not isinstance(manifest, Mapping) or manifest.get("root_id") != "control":
            continue
        document_type = manifest.get("artefact_type")
        if document_type not in _DOCUMENT_ACTIONS_BY_TYPE:
            continue
        relative = manifest.get("relative_path")
        digest = manifest.get("content_sha256")
        artefact_id = manifest.get("artefact_id")
        if not all(isinstance(value, str) and value for value in (relative, digest, artefact_id)):
            raise IntegrityError("registered SPEC document manifest is invalid")
        registration_events = [
            event
            for event in events
            if event.get("event_type") == "ArtefactRegistered"
            and event.get("stream_id") == artefact_id
            and event.get("payload", {}).get("manifest") == manifest
        ]
        if len(registration_events) != 1:
            raise IntegrityError("registered SPEC document has no exact registration event")
        identities.append(
            _RegisteredSpecDocumentIdentity(
                str(document_type),
                artefact_id,
                digest,
                relative,
                registration_events[0],
            )
        )

    completion_actions: dict[tuple[str, str, str, str, str], list[str]] = {}
    for event in events:
        payload = event.get("payload")
        if event.get("event_type") != "SpecFlowActionCompleted" or not isinstance(payload, Mapping):
            continue
        action = payload.get("action")
        definition = _ACTION_DEFINITIONS.get(str(action))
        if definition is None or definition.document_type is None:
            continue
        retry_id = payload.get("retry_id")
        packet_sha256 = payload.get("packet_sha256")
        if (
            payload.get("route_id") != ROUTE_ID
            or not isinstance(retry_id, str)
            or not retry_id
            or not isinstance(packet_sha256, str)
            or len(packet_sha256) != 64
            or any(character not in "0123456789abcdef" for character in packet_sha256)
            or event.get("command_payload_hash") != sha256_hex(canonical_bytes(payload))
        ):
            raise IntegrityError("registered SPEC document completion proof conflicts")
        matching_identities = [
            identity
            for identity in identities
            if payload.get("document_type") == identity.document_type == definition.document_type
            and payload.get("artefact_id") == identity.artefact_id
            and payload.get("content_sha256") == identity.content_sha256
            and payload.get("registration_event_id") == identity.registration_event.get("event_id")
            and payload.get("registration_event_sha256") == identity.registration_event.get("event_hash")
        ]
        if len(matching_identities) != 1:
            raise IntegrityError("registered SPEC document completion proof conflicts")
        completion_actions.setdefault(matching_identities[0].completion_key, []).append(str(action))

    records: list[_RegisteredSpecDocument] = []
    for identity in identities:
        try:
            raw = read_contained_regular_file(
                operator.control_root,
                identity.relative_path,
                label="registered SPEC document",
            )
            value = json.loads(raw)
            if raw != canonical_bytes(value) or sha256_hex(raw) != identity.content_sha256:
                raise IntegrityError("registered SPEC document binding differs")
            if not isinstance(value, dict):
                raise IntegrityError("registered SPEC document is not an object")
            _validate_spec_document_content(operator, document_type=identity.document_type, document=value)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, IntegrityError) as exc:
            if identity.completion_key in completion_actions:
                if isinstance(exc, IntegrityError):
                    raise
                raise IntegrityError("registered SPEC document is unavailable") from exc
            # A generic RegisterArtefact event is not SPEC completion proof.
            # Malformed unproven content is therefore outside this census.
            continue
        records.append(
            _RegisteredSpecDocument(
                identity.document_type,
                identity.artefact_id,
                identity.content_sha256,
                identity.registration_event,
                value,
            )
        )

    found: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        document_type = record.document_type
        artefact_id = record.artefact_id
        digest = record.content_sha256
        registration_event = record.registration_event
        completion_key = (
            document_type,
            artefact_id,
            digest,
            str(registration_event.get("event_id")),
            str(registration_event.get("event_hash")),
        )
        proven_actions = completion_actions.get(completion_key, ())
        if proven_actions:
            if len(proven_actions) != 1:
                raise IntegrityError("registered SPEC document completion proof conflicts")
            proven_action = proven_actions[0]
        else:
            legacy_actions = [
                action
                for action in _DOCUMENT_ACTIONS_BY_TYPE[document_type]
                if _legacy_document_was_consumed(
                    events,
                    projection,
                    records,
                    record,
                    action=action,
                )
            ]
            if not legacy_actions:
                continue
            if len(legacy_actions) != 1:
                raise IntegrityError(f"multiple completed SPEC actions claim document type: {document_type}")
            proven_action = legacy_actions[0]
        value = record.value
        expected_action = _DOCUMENT_ACTIONS_BY_TYPE[document_type][0]
        if len(_DOCUMENT_ACTIONS_BY_TYPE[document_type]) > 1:
            outcome = value.get("outcome")
            expected_action = {
                "COMPLETE": next(
                    action for action in _DOCUMENT_ACTIONS_BY_TYPE[document_type] if action.endswith("_complete")
                ),
                "PARTIAL": next(
                    action for action in _DOCUMENT_ACTIONS_BY_TYPE[document_type] if action.endswith("_partial")
                ),
            }.get(str(outcome), "")
        if proven_action != expected_action:
            raise IntegrityError("registered SPEC document differs from its completed action")
        found.setdefault(document_type, []).append(value)
    for kind, values in found.items():
        if len(values) != 1:
            raise IntegrityError(f"duplicate registered SPEC document: {kind}")
    return found


def _validate_spec_document_content(
    operator: DiscoveryOperator,
    *,
    document_type: str,
    document: Mapping[str, Any],
) -> None:
    """Validate one registered document from its manifest-selected contract."""

    schema_id = _DOCUMENT_SCHEMA_BY_TYPE.get(document_type)
    if schema_id is None or document.get("document_type") != document_type or document.get("route_id") != ROUTE_ID:
        raise IntegrityError("registered SPEC document type or route binding differs")
    try:
        operator.schemas.validate(schema_id, document, schema_version="1.0.0")
    except SchemaError as exc:
        raise IntegrityError("registered SPEC document schema is invalid") from exc
    if document_type in {"spec_01_operator_brief", "spec_02_operator_brief"}:
        manifest = document.get("brief_manifest")
        if not isinstance(manifest, Mapping):
            raise IntegrityError("registered SPEC brief has no accepted brief manifest")
        try:
            operator.schemas.validate("ars://methods/brief-manifest", manifest)
        except SchemaError as exc:
            raise IntegrityError("registered SPEC brief manifest is invalid") from exc
        if document.get("brief_manifest_sha256") != sha256_hex(canonical_bytes(manifest)):
            raise IntegrityError("registered SPEC brief does not bind its exact manifest")


def _actor_for_row(
    events: Sequence[Mapping[str, Any]], row: str, projection: Mapping[str, Any], *, dossier_id: str | None = None
) -> str | None:
    return _SpecRouteCensus.from_snapshot(events, projection, dossier_id=dossier_id).actor_for_row(row)


class SpecFlow:
    """One stage-aware, provider-free SPEC route coordinator."""

    def __init__(self, operator: DiscoveryOperator) -> None:
        self.operator = operator
        self.route = _validate_route(operator)
        expected_set = build_spec_authority_subject(operator.repository_root, "dossier_expected_set").get(
            "expected_set"
        )
        if not isinstance(expected_set, Mapping) or not isinstance(expected_set.get("dossier_id"), str):
            raise ConfigurationError("SPEC route dossier identity is unavailable")
        self._dossier_id = expected_set["dossier_id"]

    def _route_census(self, events: Sequence[Mapping[str, Any]], projection: Mapping[str, Any]) -> _SpecRouteCensus:
        return _SpecRouteCensus.from_snapshot(events, projection, dossier_id=self._dossier_id)

    def _runtime(self) -> DiscoveryRuntime:
        return DiscoveryRuntime(
            self.operator.control_root,
            self.operator.ledger,
            self.operator.schemas,
            catalogue_path=self.operator.catalogue_path,
            authority_resolver=self.operator.authority_resolver,
            clock=self.operator.clock,
            repository_root=self.operator.repository_root,
            root_tokens=self.operator.root_tokens,
            operational_ledger=self.operator.ledger,
        )

    def _trusted_now(self) -> datetime:
        """Return the operator clock as one validated UTC instant."""

        try:
            value = self.operator.clock()
        except Exception as exc:
            raise IntegrityError("SPEC operator clock is unavailable") from exc
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise IntegrityError("SPEC operator clock must return an aware datetime")
        try:
            offset = value.utcoffset()
            normalized = value.astimezone(UTC)
        except Exception as exc:
            raise IntegrityError("SPEC operator clock must return an aware datetime") from exc
        if offset is None:
            raise IntegrityError("SPEC operator clock must return an aware datetime")
        return normalized

    def _snapshot(self) -> tuple[tuple[dict[str, Any], ...], dict[str, Any], dict[str, list[dict[str, Any]]]]:
        events = self.operator.ledger.snapshot().events
        recover_registered_content(self.operator.control_root, events)
        events = self.operator.ledger.snapshot().events
        projection = self._runtime().replay(events)
        documents = _registered_documents(self.operator, events, projection)
        return events, projection, documents

    def _prevalidate_lifecycle_grant(
        self,
        *,
        grant_id: str,
        actor_id: str,
        command_type: str,
        subject_kind: str,
        subject_id: str,
        now: datetime,
    ) -> None:
        binding = self.operator.schemas.command_binding(command_type)
        if binding is None:
            raise IntegrityError(f"{command_type} has no active schema binding")
        identity = self.operator.schemas.resolve_identity(binding.schema_id, binding.schema_version)
        self.operator.authority_resolver.resolve_lifecycle_command(
            grant_id=grant_id,
            actor_id=actor_id,
            command=GrantedCommandIdentity(
                command_type=command_type,
                schema_id=identity.schema_id,
                schema_version=identity.schema_version,
                schema_sha256=identity.sha256,
            ),
            required_risk="R3",
            project_id=self.operator.ledger.project_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            now=now,
        )

    def _require_owner_authenticated_approval_decision(
        self,
        *,
        document: Mapping[str, Any],
        registration: Mapping[str, Any],
    ) -> None:
        resolver = self.operator.authority_resolver
        administration = resolver.administration_context()
        authority_events = (
            EventLedger(
                resolver.control_root,
                self.operator.ledger.project_id,
                self.operator.schemas,
                store_identity=resolver.expected_store_identity,
            )
            .snapshot()
            .events
        )
        grant_id = registration.get("authority_grant_id")
        registrar_id = document.get("registrar", {}).get("actor_id")
        content_sha256 = sha256_hex(canonical_bytes(document))
        intent = {
            "target_actor_id": registrar_id,
            "target_actor_class": "agent",
            "authority_lane": "producer/spec_brief_registration",
            "actor_role": "SPEC brief producer",
            "subject_scope": {
                "project_id": self.operator.ledger.project_id,
                "subject": {"kind": "artefact", "id": registration.get("artefact_id")},
            },
            "evidence_refs": [f"{_SPEC_02_APPROVAL_EVIDENCE_PREFIX}{content_sha256}"],
            "effective_at": document.get("valid_window", {}).get("starts_at"),
            "expires_at": document.get("valid_window", {}).get("expires_at"),
            "reason": _SPEC_02_APPROVAL_AUTHORITY_REASON,
            "owner_action": "activate_authority_grant",
        }
        expected_payload_hash = sha256_hex(canonical_bytes({"intent": intent}))
        matches = []
        for event in authority_events:
            payload = event.get("payload")
            decision = payload.get("decision") if isinstance(payload, Mapping) else None
            proposed_grant = payload.get("proposed_grant") if isinstance(payload, Mapping) else None
            if (
                event.get("event_type") == "OwnerAuthorityAdministrationDecisionPublished"
                and event.get("command_type") == "PublishOwnerAuthorityAdministrationDecision"
                and event.get("actor_id") == administration.owner_actor_id
                and event.get("authority_grant_id") == administration.root_grant_id
                and event.get("command_payload_hash") == expected_payload_hash
                and isinstance(decision, Mapping)
                and decision.get("owner_actor_id") == administration.owner_actor_id
                and decision.get("target_grant_id") == grant_id
                and decision.get("subject_scope") == intent["subject_scope"]
                and decision.get("effective_at") == intent["effective_at"]
                and decision.get("expires_at") == intent["expires_at"]
                and isinstance(proposed_grant, Mapping)
                and proposed_grant.get("authority_grant_id") == grant_id
                and proposed_grant.get("actor_id") == registrar_id
                and proposed_grant.get("subject_scope") == intent["subject_scope"]
            ):
                matches.append(event)
        if len(matches) != 1:
            raise IntegrityError("SPEC-02 approval bytes lack one authenticated owner decision")

    def _action_identity(self, action: str, packet: Mapping[str, Any], *, publish: bool) -> bool:
        definition = _ACTION_DEFINITIONS.get(action)
        if definition is None or not definition.single_shot:
            return False
        value = {
            "schema_id": "ars://internal/spec-flow-action-identity",
            "schema_version": "1.0.0",
            "route_id": ROUTE_ID,
            "action": action,
            "retry_id": packet.get("retry_id"),
            "packet_sha256": sha256_hex(canonical_bytes(packet)),
        }
        prior = _read_action_identity(self.operator.control_root, action)
        if prior is not None:
            if prior != value:
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            return True
        if publish:
            store = CandidateDocumentStore(
                self.operator.control_root,
                relative_directory=_SPEC_ACTION_IDENTITY_DIRECTORY,
            )
            store.publish_bytes(action, canonical_bytes(value))
        return False

    def _prepare_action_journal(self, action: str, packet: Mapping[str, Any], *, publish: bool) -> bool:
        """Bind an exact retry before effects without treating the action as completed."""

        definition = _ACTION_DEFINITIONS.get(action)
        if definition is None or not definition.single_shot:
            return False
        value = _action_preparation_value(action, packet)
        prior = _prepared_action_journal(self.operator.control_root, action)
        if prior is not None:
            if prior != value:
                raise ConflictError("prepared SPEC action retry differs from its durable packet")
            return True
        if publish:
            CandidateDocumentStore(
                self.operator.control_root,
                relative_directory=_SPEC_ACTION_JOURNAL_DIRECTORY,
            ).publish_bytes(action, canonical_bytes(value))
        return False

    def _complete_action(self, action: str, packet: Mapping[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        definition = _ACTION_DEFINITIONS.get(action)
        if definition is not None and definition.document_type is not None:
            registration = result.get("registration")
            if not isinstance(registration, Mapping):
                raise IntegrityError("completed SPEC document lacks its registration identity")
            artefact_id = registration.get("artefact_id")
            content_sha256 = registration.get("content_sha256")
            snapshot = self.operator.ledger.snapshot()
            registration_events = [
                event
                for event in snapshot.events
                if event.get("event_type") == "ArtefactRegistered"
                and event.get("stream_id") == artefact_id
                and event.get("payload", {}).get("manifest", {}).get("content_sha256") == content_sha256
            ]
            if len(registration_events) != 1:
                raise IntegrityError("completed SPEC document lacks one exact registration event")
            registered = registration_events[0]
            completion_payload = {
                "route_id": ROUTE_ID,
                "action": action,
                "retry_id": packet.get("retry_id"),
                "packet_sha256": sha256_hex(canonical_bytes(packet)),
                "document_type": definition.document_type,
                "artefact_id": artefact_id,
                "content_sha256": content_sha256,
                "registration_event_id": registered["event_id"],
                "registration_event_sha256": registered["event_hash"],
            }
            claimed = [
                event
                for event in snapshot.events
                if event.get("event_type") == "SpecFlowActionCompleted"
                and isinstance(event.get("payload"), Mapping)
                and (event["payload"].get("action") == action or event["payload"].get("artefact_id") == artefact_id)
            ]
            if claimed:
                if len(claimed) != 1 or claimed[0].get("payload") != completion_payload:
                    raise ConflictError("completed SPEC action conflicts with its sealed ledger proof")
            else:
                command_binding = self.operator.schemas.command_binding("CompleteSpecFlowAction")
                event_binding = self.operator.schemas.event_binding("SpecFlowActionCompleted", "CompleteSpecFlowAction")
                if command_binding is None or event_binding is None:
                    raise IntegrityError("SPEC action completion schema binding is unavailable")
                command_identity = self.operator.schemas.resolve_identity(
                    command_binding.schema_id, command_binding.schema_version
                )
                occurred_at = self._trusted_now().isoformat().replace("+00:00", "Z")
                self.operator.ledger._append_spec_flow_action_from_validated_service(
                    {
                        "event_type": "SpecFlowActionCompleted",
                        "schema_id": event_binding.schema_id,
                        "schema_version": event_binding.schema_version,
                        "stream_id": new_id("dispatch"),
                        "command_id": new_id("command"),
                        "command_type": "CompleteSpecFlowAction",
                        "command_schema_id": command_identity.schema_id,
                        "command_schema_version": command_identity.schema_version,
                        "command_schema_sha256": command_identity.sha256,
                        "idempotency_key": f"spec-flow-complete:{action}:{packet.get('retry_id')}",
                        "command_payload_hash": sha256_hex(canonical_bytes(completion_payload)),
                        "correlation_id": str(packet.get("retry_id")),
                        "causation_id": registered["event_id"],
                        "actor_id": registered["actor_id"],
                        "authority_grant_id": registered["authority_grant_id"],
                        "occurred_at": occurred_at,
                        "payload": completion_payload,
                    },
                    snapshot=snapshot,
                    session=_issue_validated_service_session(self.operator.ledger),
                )
        self._action_identity(action, packet, publish=True)
        result["status"] = asdict(self.status())
        return result

    @staticmethod
    def _registration_event_matches(events: Sequence[Mapping[str, Any]], command: Mapping[str, Any]) -> bool:
        matches = [
            event
            for event in events
            if event.get("event_type") == "ArtefactRegistered"
            and event.get("stream_id") == command.get("target_stream_id")
        ]
        if len(matches) != 1:
            return False
        event = matches[0]
        # Keep the comparison limited to identities that the event envelope
        # durably records; submitted_at/reason/evidence are represented by the
        # canonical payload and command identity rather than copied verbatim.
        return (
            all(
                event.get(key) == command.get(key)
                for key in (
                    "command_id",
                    "command_type",
                    "actor_id",
                    "authority_grant_id",
                    "idempotency_key",
                    "correlation_id",
                    "causation_id",
                    "project_id",
                )
            )
            and event.get("command_payload_hash") == sha256_hex(canonical_bytes(command.get("payload")))
            and event.get("payload") == command.get("payload")
        )

    def _validate_completed_document_retry(
        self,
        action: str,
        packet: Mapping[str, Any],
        events: Sequence[Mapping[str, Any]],
        projection: Mapping[str, Any],
        documents: Mapping[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        definition = _ACTION_DEFINITIONS[action]
        if definition.document_type is None:  # pragma: no cover - caller architecture fence
            raise RuntimeError("completed document retry requires a document action")
        document_type = definition.document_type
        durable = documents.get(document_type, ())
        if len(durable) != 1:
            raise IntegrityError("completed SPEC document action has no exact durable document")
        registrations = packet.get("registration")
        supplied_document = packet.get("document")
        candidate_registration = (
            registrations.get("package_registration")
            if action in {"prepare_spec_01", "prepare_spec_02"} and isinstance(registrations, Mapping)
            else registrations
        )
        package_id = candidate_registration.get("artefact_id") if isinstance(candidate_registration, Mapping) else None
        stream_state = projection.get("artefact_streams", {}).get(package_id) if isinstance(package_id, str) else None
        stream_manifest = stream_state.get("manifest") if isinstance(stream_state, Mapping) else None
        durable_sha256 = sha256_hex(canonical_bytes(durable[0]))
        if (
            not isinstance(candidate_registration, dict)
            or not isinstance(package_id, str)
            or not isinstance(stream_manifest, Mapping)
            or stream_manifest.get("artefact_type") != document_type
            or stream_manifest.get("artefact_id") != package_id
            or stream_manifest.get("content_sha256") != durable_sha256
            or stream_state.get("content_sha256") != durable_sha256
        ):
            raise IntegrityError("completed SPEC document action has no exact durable registration")
        context_id: str | None = None
        brief: Mapping[str, Any] | None = None
        if action in {"prepare_spec_01", "prepare_spec_02"}:
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
            if not isinstance(supplied_document, dict) or set(supplied_document) != required_semantic:
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            if not isinstance(registrations, dict) or set(registrations) != {
                "context_authority_grant_id",
                "brief_registration",
                "package_registration",
            }:
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            package = durable[0]
            context_id = derive_spec_owner_context_id(
                actor_id=str(supplied_document["operator_actor_id"]),
                operator_session_id=str(supplied_document["operator_session_id"]),
                recipient_id=str(supplied_document["recipient_id"]),
                purpose=str(supplied_document["purpose"]),
                scope=str(supplied_document["scope"]),
                application_version=str(supplied_document["application_version"]),
                valid_from=str(supplied_document["evaluation_time"]),
                expires_at=str(supplied_document["handoff_expires_at"]),
                retry_identity=str(packet["retry_id"]),
            )
            manifest = package.get("brief_manifest")
            context = manifest.get("context_packet") if isinstance(manifest, Mapping) else None
            if (
                not isinstance(context, Mapping)
                or context.get("context_id") != context_id
                or manifest.get("brief_purpose") != supplied_document["purpose"]
                or manifest.get("created_at") != supplied_document["created_at"]
                or package.get("operator_session")
                != {
                    "session_id": supplied_document["operator_session_id"],
                    "operator_actor_id": supplied_document["operator_actor_id"],
                    "application": "Codex desktop",
                    "application_version": supplied_document["application_version"],
                    "manually_operated": True,
                }
            ):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            registration = candidate_registration
            brief_registration = registrations.get("brief_registration")
            if (
                not isinstance(registration, dict)
                or not isinstance(brief_registration, dict)
                or brief_registration.get("artefact_id") != manifest.get("brief_artefact_id")
                or not any(
                    event.get("stream_id") == context_id
                    and event.get("authority_grant_id") == registrations.get("context_authority_grant_id")
                    for event in events
                )
            ):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            brief_id = str(brief_registration["artefact_id"])
            brief_state = projection.get("artefact_streams", {}).get(brief_id)
            brief_manifest = brief_state.get("manifest") if isinstance(brief_state, Mapping) else None
            if not isinstance(brief_manifest, Mapping):
                raise IntegrityError("completed SPEC brief registration is unavailable")
            try:
                brief_value = json.loads(
                    read_contained_regular_file(
                        self.operator.control_root,
                        brief_manifest.get("relative_path"),
                        label="completed SPEC brief",
                    )
                )
                prepared_brief = prepare_candidate_document(
                    value=brief_value,
                    registration=CandidateRegistration(**deepcopy(brief_registration)),
                    document_store=CandidateDocumentStore(
                        self.operator.control_root,
                        relative_directory=Path("methods/documents/spec-flow"),
                    ),
                )
            except (OSError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
                raise ConflictError("completed SPEC action retry differs from its durable packet") from exc
            if not self._registration_event_matches(events, prepared_brief.command):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            brief = package
        else:
            if supplied_document != durable[0] or not isinstance(registrations, dict):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            registration = registrations
        try:
            prepared = prepare_candidate_document(
                value=durable[0],
                registration=CandidateRegistration(**deepcopy(registration)),
                document_store=CandidateDocumentStore(
                    self.operator.control_root,
                    relative_directory=Path("methods/documents/spec-flow"),
                ),
            )
        except (TypeError, ValueError) as exc:
            raise ConflictError("completed SPEC action retry differs from its durable packet") from exc
        if not self._registration_event_matches(events, prepared.command):
            raise ConflictError("completed SPEC action retry differs from its durable packet")
        receipt_store = ReceiptStore(self.operator.control_root)
        registration_receipt = receipt_store.load(str(prepared.command["command_id"]))
        if registration_receipt is None or registration_receipt.status != "accepted":
            raise IntegrityError("completed SPEC document registration receipt is unavailable")
        receipts = []
        for command in packet.get("commands", ()):
            if not isinstance(command, Mapping):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            receipt = receipt_store.load(str(command.get("command_id")))
            if receipt is None or receipt.status != "accepted":
                raise IntegrityError("completed SPEC action route receipt is unavailable")
            receipts.append(asdict(receipt))
        result: dict[str, Any] = {
            "route_id": ROUTE_ID,
            "action": action,
            "retry_id": packet["retry_id"],
            "registration": {
                "artefact_id": package_id,
                "content_sha256": prepared.content_sha256,
                "receipt": asdict(registration_receipt),
            },
            "receipts": receipts,
        }
        if context_id is not None and brief is not None:
            result.update({"context_id": context_id, "brief": brief})
        return result

    def _completed_brief_input_result(
        self,
        action: str,
        packet: Mapping[str, Any],
        projection: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Reconstruct one completed brief-input result without live admission checks."""

        definition = _ACTION_DEFINITIONS[action]
        if definition.brief_input_state is None:  # pragma: no cover - caller architecture fence
            raise RuntimeError("completed brief-input result requires a brief-input action")
        if action == "register_spec_01_brief_inputs":
            registration = packet.get("registration")
            entries = registration.get("raw_publications") if isinstance(registration, Mapping) else None
            states = self._brief_input_states(projection)
            if not isinstance(entries, list) or len(entries) != len(states):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            registrations = []
            for entry in entries:
                candidate = entry.get("registration") if isinstance(entry, Mapping) else None
                artefact_id = candidate.get("artefact_id") if isinstance(candidate, Mapping) else None
                state = states.get(str(artefact_id))
                if state is None or not isinstance(state.get("content_sha256"), str):
                    raise ConflictError("completed SPEC action retry differs from its durable packet")
                registrations.append(
                    {
                        "artefact_id": str(artefact_id),
                        "content_sha256": state["content_sha256"],
                    }
                )
            if {item["artefact_id"] for item in registrations} != set(states):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            receipts: list[dict[str, Any]] = []
            registration_result: list[dict[str, Any]] | None = registrations
        else:
            receipt_store = ReceiptStore(self.operator.control_root)
            receipts = []
            for command in packet.get("commands", ()):
                if not isinstance(command, Mapping):
                    raise ConflictError("completed SPEC action retry differs from its durable packet")
                receipt = receipt_store.load(str(command.get("command_id")))
                if receipt is None or receipt.status not in {"accepted", "replayed"}:
                    raise IntegrityError("completed SPEC brief-input receipt is unavailable")
                receipts.append(asdict(receipt))
            registration_result = None
        return {
            "route_id": ROUTE_ID,
            "action": action,
            "retry_id": packet["retry_id"],
            "registration": registration_result,
            "receipts": receipts,
        }

    def _expected_brief_input_census(self) -> dict[str, dict[str, Any]]:
        route_sources = {
            str(source["locator"]): source
            for source in self.route["sources"]
            if source.get("alias") in {"SPEC-01", "SPEC-02"}
        }
        census: dict[str, dict[str, Any]] = {}
        for source_path, artefact_type in _BRIEF_INPUT_SOURCE_TYPES.items():
            try:
                raw = (self.operator.repository_root / source_path).read_bytes()
            except OSError as exc:
                raise IntegrityError("SPEC brief input source is unavailable") from exc
            content_sha256 = sha256_hex(raw)
            route_source = route_sources.get(source_path)
            if artefact_type == "spec_operator_source" and (
                not isinstance(route_source, Mapping)
                or route_source.get("sha256") != content_sha256
                or route_source.get("size_bytes") != len(raw)
            ):
                raise IntegrityError("SPEC brief input differs from the exact route source")
            artefact_id = spec_brief_input_artefact_id(source_path, content_sha256)
            census[artefact_id] = {
                "artefact_id": artefact_id,
                "artefact_type": artefact_type,
                "source_relative_path": source_path,
                "relative_path": f"{_BRIEF_INPUT_DESTINATION_PREFIX}{artefact_id}.md",
                "content_sha256": content_sha256,
                "size_bytes": len(raw),
                "media_type": "text/markdown; charset=utf-8",
            }
        return census

    def _brief_input_states(self, projection: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        census = self._expected_brief_input_census()
        expected_by_signature: dict[tuple[object, ...], Mapping[str, Any]] = {}
        for expected in census.values():
            signature = tuple(expected[key] for key in ("artefact_type", "content_sha256", "size_bytes", "media_type"))
            if signature in expected_by_signature:
                raise IntegrityError("multiple route sources bind one exact SPEC brief input")
            expected_by_signature[signature] = expected

        matches: dict[tuple[object, ...], list[tuple[str, Mapping[str, Any]]]] = {}
        streams = projection.get("artefact_streams", {})
        if not isinstance(streams, Mapping):
            return {}
        for stream_id, state in streams.items():
            manifest = state.get("manifest") if isinstance(state, Mapping) else None
            identity = str(stream_id)
            if not isinstance(manifest, Mapping):
                continue
            signature = (
                manifest.get("artefact_type"),
                state.get("content_sha256"),
                manifest.get("size_bytes"),
                manifest.get("media_type"),
            )
            expected = expected_by_signature.get(signature)
            if (
                expected is None
                or manifest.get("artefact_id") != identity
                or manifest.get("root_id") != "control"
                or manifest.get("relative_path") != f"{_BRIEF_INPUT_DESTINATION_PREFIX}{identity}.md"
                or manifest.get("content_sha256") != expected["content_sha256"]
            ):
                continue
            matches.setdefault(signature, []).append((identity, state))
        if any(len(rows) > 1 for rows in matches.values()):
            raise IntegrityError("multiple registered streams bind one exact SPEC brief input")
        return {identity: state for rows in matches.values() for identity, state in rows}

    def _pending_brief_input_authority_states(
        self, projection: Mapping[str, Any], command_type: str
    ) -> dict[str, Mapping[str, Any]]:
        inputs = self._brief_input_states(projection)
        if command_type == "RecordScientificReview":
            return {stream_id: state for stream_id, state in inputs.items() if not state.get("scientific_reviews")}
        if command_type == "SetArtefactUseAuthority":
            return {
                stream_id: state
                for stream_id, state in inputs.items()
                if state.get("use_authority") != "accepted_for_scope"
            }
        raise IntegrityError("SPEC brief-input authority command type is unsupported")

    @staticmethod
    def _document_proves_action(action: str, document: Mapping[str, Any]) -> bool:
        definition = _ACTION_DEFINITIONS.get(action)
        document_type = definition.document_type if definition is not None else None
        if document_type is None or document.get("document_type") != document_type:
            return False
        actions = _DOCUMENT_ACTIONS_BY_TYPE[document_type]
        if len(actions) == 1:
            return actions[0] == action
        expected_outcome = "PARTIAL" if action.endswith("_partial") else "COMPLETE"
        return document.get("outcome") == expected_outcome

    def _action_effects_are_complete(
        self,
        action: str,
        *,
        completed_rows: set[str],
        documents: Mapping[str, list[dict[str, Any]]],
        projection: Mapping[str, Any],
    ) -> bool:
        """Evaluate one action only from all durable effects in its definition."""

        definition = _ACTION_DEFINITIONS.get(action)
        if definition is None or not set(definition.required_rows).issubset(completed_rows):
            return False
        if definition.document_type is not None:
            durable = documents.get(definition.document_type, ())
            if len(durable) != 1 or not self._document_proves_action(action, durable[0]):
                return False
        if definition.brief_input_state is not None:
            brief_inputs = self._brief_input_states(projection)
            expected_count = len(self._expected_brief_input_census())
            if not expected_count or len(brief_inputs) != expected_count:
                return False
            if definition.brief_input_state in {"reviewed", "accepted"} and any(
                not state.get("scientific_reviews") for state in brief_inputs.values()
            ):
                return False
            if definition.brief_input_state == "accepted" and any(
                state.get("use_authority") != "accepted_for_scope" for state in brief_inputs.values()
            ):
                return False
        return True

    def _action_state(
        self,
        action: str,
        *,
        completed_rows: set[str],
        documents: Mapping[str, list[dict[str, Any]]],
        projection: Mapping[str, Any],
        events: Sequence[Mapping[str, Any]],
        prepared: bool,
    ) -> _SpecActionState:
        """Resolve not-started, prepared, or completed from one action definition."""

        definition = _ACTION_DEFINITIONS[action]
        effects_complete = self._action_effects_are_complete(
            action,
            completed_rows=completed_rows,
            documents=documents,
            projection=projection,
        )
        if definition.document_type is not None:
            completion_sealed = any(
                event.get("event_type") == "SpecFlowActionCompleted"
                and event.get("payload", {}).get("action") == action
                for event in events
            )
        elif definition.single_shot:
            completion_sealed = _read_action_identity(self.operator.control_root, action) is not None
        else:
            completion_sealed = effects_complete
        if effects_complete and (completion_sealed or not prepared):
            return _SpecActionState(definition, "completed", effects_complete, completion_sealed)
        if prepared:
            return _SpecActionState(definition, "prepared", effects_complete, completion_sealed)
        return _SpecActionState(definition, "not_started", effects_complete, completion_sealed)

    def status(self) -> SpecFlowStatus:
        events, projection, documents = self._snapshot()
        return self._status_from_snapshot(events, projection, documents)

    def _status_from_snapshot(
        self,
        events: Sequence[Mapping[str, Any]],
        projection: Mapping[str, Any],
        documents: Mapping[str, list[dict[str, Any]]],
    ) -> SpecFlowStatus:
        """Render public status from the same immutable snapshot used for admission."""

        census = self._route_census(events, projection)
        rows = set(census.rows)
        pending = _pending_action_preparation(self.operator.control_root, events)
        if pending is not None:
            action = str(pending["action"])
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                f"{action}_prepared",
                action,
                "the exact prepared SPEC action must be retried before any later route action",
            )

        def action_completed(action: str) -> bool:
            return (
                self._action_state(
                    action,
                    completed_rows=rows,
                    documents=documents,
                    projection=projection,
                    events=events,
                    prepared=False,
                ).phase
                == "completed"
            )

        completed = "none"
        for action in _INITIAL_ACTION_SEQUENCE:
            if not action_completed(action):
                authority_kind = {
                    "bootstrap_dossier_authority": "dossier_expected_set",
                    "bootstrap_path_authority": "path_registration",
                }.get(action)
                if authority_kind is not None:
                    build_spec_authority_subject(self.operator.repository_root, authority_kind)
                return SpecFlowStatus(
                    "NOT_RUNNABLE",
                    completed,
                    action,
                    "exact action identities, evidence, and active authority are required",
                )
            completed = action
        if not action_completed("register_spec_01_brief_inputs"):
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "request_spec_01",
                "register_spec_01_brief_inputs",
                "exact committed SPEC-01/SPEC-02 sources and required Methods Pack assets must be registered",
            )
        if not action_completed("review_spec_01_brief_inputs"):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "spec_01_brief_inputs_registered",
                "review_spec_01_brief_inputs",
                "registered brief inputs await independent exact-subject use review",
            )
        if not action_completed("accept_spec_01_brief_inputs"):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "spec_01_brief_inputs_reviewed",
                "accept_spec_01_brief_inputs",
                "reviewed brief inputs await explicit accepted-for-scope authority",
            )
        if not action_completed("prepare_spec_01"):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "request_spec_01",
                "prepare_spec_01",
                "Codex desktop brief export and operator session identity are required",
            )
        completed_returns = [
            action for action in ("return_spec_01_complete", "return_spec_01_partial") if action_completed(action)
        ]
        if len(completed_returns) > 1:
            raise IntegrityError("multiple SPEC-01 return branches are completed")
        if not completed_returns:
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "prepare_spec_01",
                "return_spec_01",
                "manually produced SPEC-01 return evidence is required",
            )
        partial_assay = completed_returns[0] == "return_spec_01_partial"
        review_action = "review_spec_01_partial" if partial_assay else "review_spec_01_complete"
        if not action_completed(review_action):
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
        if not action_completed("decide_spec_01"):
            return SpecFlowStatus(
                "OWNER_BLOCKED", "review_spec_01", "decide_spec_01", "explicit owner PROMOTE, PARK, or KILL is required"
            )
        candidates = [projection["candidates"].get(value) for value in census.candidate_ids]
        if len(candidates) != 1 or not isinstance(candidates[0], Mapping):
            return SpecFlowStatus(
                "NOT_RUNNABLE", "decide_spec_01", None, "exact SPEC route Candidate cannot be resolved"
            )
        candidate_status = candidates[0].get("status")
        if candidate_status == "killed":
            return SpecFlowStatus("PROVEN", "spec_01_killed", None, "owner decision KILLED is terminal")
        correction_completed = action_completed("correct_spec_01_source")
        approval_completed = action_completed("approve_spec_02")
        if candidate_status == "parked" and not correction_completed:
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "spec_01_parked",
                "correct_spec_01_source",
                "the recorded paper-code availability finding must be corrected before any later test",
            )
        if candidate_status == "parked" and not approval_completed:
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "spec_01_parked_corrected",
                "approve_spec_02",
                "a separate owner-approved route-validation run is required because PARK remains the scientific disposition",
            )
        if candidate_status not in {
            "parked",
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
        if not approval_completed:
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "spec_01_promoted",
                "approve_spec_02",
                "separate durable Stephen live-run approval is required",
            )
        if not action_completed("prepare_spec_02"):
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "approve_spec_02",
                "prepare_spec_02",
                "Codex desktop SPEC-02 brief preparation is required",
            )
        if not action_completed("start_spec_02"):
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "prepare_spec_02",
                "start_spec_02",
                "exact operational lease, attempt, limits, and authority are required",
            )
        completed_spike_returns = [
            action for action in ("return_spec_02_complete", "return_spec_02_partial") if action_completed(action)
        ]
        if len(completed_spike_returns) > 1:
            raise IntegrityError("multiple SPEC-02 return branches are completed")
        if not completed_spike_returns:
            return SpecFlowStatus(
                "OWNER_BLOCKED",
                "start_spec_02",
                "return_spec_02",
                "manually produced SPEC-02 evidence is required; no model is launched",
            )
        partial_spike = completed_spike_returns[0] == "return_spec_02_partial"
        spike_review_action = "review_spec_02_partial" if partial_spike else "review_spec_02_complete"
        if not action_completed(spike_review_action):
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
        if not action_completed("decide_spec_02"):
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
        definition = _ACTION_DEFINITIONS.get(action)
        expected = definition.required_rows if definition is not None else ()
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

    def _validate_roles(self, commands: Sequence[Mapping[str, Any]], census: _SpecRouteCensus) -> None:
        if not commands:
            return
        command = Command(deepcopy(commands[-1]))
        row, _route = discovery_route(command)
        actor = commands[-1].get("actor_id")
        producer = census.actor_for_row("OR-004") or census.actor_for_row("OR-005")
        reviewer = census.actor_for_row("OR-006") or census.actor_for_row("OR-007")
        if row in {"OR-006", "OR-007"} and actor == producer:
            raise IntegrityError("SPEC-01 reviewer must be independent of the producer")
        if row == "OR-013" and actor == reviewer:
            raise IntegrityError("SPEC-01 owner decider must be distinct from the reviewer")
        spike_producer = census.actor_for_row("OR-018") or census.actor_for_row("OR-019")
        spike_reviewer = census.actor_for_row("OR-020") or census.actor_for_row("OR-021")
        if row in {"OR-020", "OR-021"} and actor == spike_producer:
            raise IntegrityError("SPEC-02 reviewer must be independent of the producer")
        if row == "OR-027" and actor == spike_reviewer:
            raise IntegrityError("SPEC-02 owner decider must be distinct from the reviewer")

    def _register_document(
        self,
        action: str,
        packet: Mapping[str, Any],
        document: Any,
        registration: Any,
        commands: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        if (
            not isinstance(document, dict)
            or document.get("document_type") != _ACTION_DEFINITIONS[action].document_type
            or document.get("route_id") != ROUTE_ID
        ):
            raise IntegrityError("SPEC document type or route binding differs")
        _validate_spec_document_content(
            self.operator,
            document_type=str(_ACTION_DEFINITIONS[action].document_type),
            document=document,
        )
        if (
            isinstance(registration, dict)
            and set(registration) == _REGISTRATION_FIELDS
            and isinstance(registration.get("manifest"), dict)
            and registration["manifest"].get("artefact_type") != document["document_type"]
        ):
            raise IntegrityError("SPEC document registration type differs from its validated document")
        if action.startswith("prepare_spec_"):
            manifest = document.get("brief_manifest")
            if not isinstance(manifest, dict):  # already guaranteed by the shared content validator
                raise IntegrityError("SPEC brief package has no accepted brief manifest")
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
            hashes: dict[object, object] = {}
            for item in document.get("artifact_hashes", ()):
                if not isinstance(item, Mapping) or item.get("name") in hashes:
                    raise IntegrityError("SPEC return artefact hash names must be unique")
                hashes[item.get("name")] = item.get("sha256")
            if hashes.get("embedded_artefact") != embedded_sha256:
                raise IntegrityError("SPEC return does not bind the embedded artefact hash")
            if len(commands) != 1 or not isinstance(commands[0], Mapping):
                raise IntegrityError("SPEC return requires one exact producer command")
            command = commands[0]
            command_payload = command.get("payload")
            producer = document.get("producer")
            if (
                not isinstance(command_payload, Mapping)
                or not isinstance(producer, Mapping)
                or producer.get("actor_id") != command.get("actor_id")
            ):
                raise IntegrityError("SPEC return producer differs from its route command actor")
            if action.startswith("return_spec_01"):
                expected_relation = command_payload.get("producer_relation_sha256")
            else:
                spike_id = command_payload.get("spike_id")
                spike = projection.get("spikes", {}).get(spike_id)
                relation = spike.get("execution_authority_relation") if isinstance(spike, Mapping) else None
                expected_relation = sha256_hex(canonical_bytes(relation)) if isinstance(relation, Mapping) else None
            if producer.get("relation_sha256") != expected_relation:
                raise IntegrityError("SPEC return producer relation differs from its route command")
            if action.startswith("return_spec_02") and not {
                "raw_output",
                "source",
                "checks",
                "result",
                "embedded_artefact",
            }.issubset(hashes):
                raise IntegrityError("SPEC-02 return omits a required raw output/source/check/result hash")
            if action.startswith("return_spec_02"):
                spike = projection.get("spikes", {}).get(command_payload.get("spike_id"))
                if not _spec_02_return_evidence_matches(
                    document,
                    projection=projection,
                    control_root=self.operator.control_root,
                    candidate_id=command_payload.get("candidate_id"),
                    spike=spike,
                ):
                    raise IntegrityError("SPEC-02 return evidence does not resolve to exact attempt artefacts")
        if action == "approve_spec_02":
            events, projection, _documents = self._snapshot()
            census = self._route_census(events, projection)
            owner_actor = census.actor_for_row("OR-013")
            administration = self.operator.authority_resolver.administration_context()
            if (
                owner_actor != administration.owner_actor_id
                or document.get("owner", {}).get("actor_id") != administration.owner_actor_id
            ):
                raise IntegrityError("SPEC-02 approval is not bound to the authenticated project owner")
            if document.get("registrar", {}).get("actor_id") == owner_actor:
                raise IntegrityError("SPEC-02 approval owner and registrar must be independent")
            if (
                not isinstance(registration, Mapping)
                or registration.get("authority_grant_id")
                not in self.operator.authority_resolver.owner_published_grant_ids()
            ):
                raise IntegrityError("SPEC-02 approval registrar lacks owner-published exact-subject authority")
            self._require_owner_authenticated_approval_decision(
                document=document,
                registration=registration,
            )
            source = next(item for item in self.route["sources"] if item["alias"] == "SPEC-02")
            if document.get("spec_02_subject", {}).get("sha256") != source["sha256"]:
                raise IntegrityError("SPEC-02 approval subject differs from the governed source")
            if document.get("brief_identity", {}).get("sha256") != source["sha256"]:
                raise IntegrityError("SPEC-02 approval does not bind the governed brief identity")
            promotion_events = [
                event
                for event in census.events
                if isinstance(event.get("payload"), Mapping) and event["payload"].get("row_id") == "OR-013"
            ]
            promotion = document.get("spec_01_promotion", {})
            if len(promotion_events) != 1 or (
                promotion.get("id") != promotion_events[0].get("event_id")
                or promotion.get("sha256") != promotion_events[0].get("event_hash")
            ):
                raise IntegrityError("SPEC-02 approval does not bind the exact SPEC-01 promotion")
            selected_option = promotion_events[0].get("payload", {}).get("selected_option")
            entry_mode = document.get("entry_mode")
            correction_ref = document.get("source_correction")
            corrections = self._snapshot()[2].get("spec_01_source_correction", ())
            if entry_mode == "standard_promotion":
                if selected_option != "PROMOTE" or correction_ref is not None:
                    raise IntegrityError("standard SPEC-02 approval requires an exact PROMOTE decision")
            elif entry_mode == "owner_approved_park_test":
                if selected_option != "PARK" or len(corrections) != 1:
                    raise IntegrityError("PARK test approval requires one durable SPEC-01 source correction")
                correction = corrections[0]
                expected_correction_ref = {
                    "id": correction.get("correction_id"),
                    "sha256": sha256_hex(canonical_bytes(correction)),
                }
                if correction_ref != expected_correction_ref or document.get("scientific_promotion") is not False:
                    raise IntegrityError("PARK test approval does not bind the exact correction and non-promotion")
            else:
                raise IntegrityError("SPEC-02 approval entry mode is unsupported")
            try:
                approved = datetime.fromisoformat(document["approved_at"].replace("Z", "+00:00"))
                starts = datetime.fromisoformat(document["valid_window"]["starts_at"].replace("Z", "+00:00"))
                expires = datetime.fromisoformat(document["valid_window"]["expires_at"].replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityError("SPEC-02 approval window is invalid") from exc
            trusted_now = self._trusted_now()
            if not starts <= approved <= trusted_now < expires:
                raise IntegrityError("SPEC-02 approval is outside its explicit live-run window")
        if action == "correct_spec_01_source":
            events, projection, _documents = self._snapshot()
            census = self._route_census(events, projection)
            assays = [
                value
                for value in projection.get("assays", {}).values()
                if isinstance(value, Mapping) and value.get("candidate_id") in census.candidate_ids
            ]
            decisions = [
                event
                for event in census.events
                if event.get("event_type") == "CandidatePromotionApplied"
                and isinstance(event.get("payload"), Mapping)
                and event["payload"].get("row_id") == "OR-013"
            ]
            if len(assays) != 1 or len(decisions) != 1:
                raise IntegrityError("SPEC-01 correction cannot resolve one assay and owner decision")
            assay = assays[0]
            decision = decisions[0]
            if document.get("scorecard_ref") != {
                "id": assay.get("assay_id"),
                "sha256": assay.get("scorecard_sha256"),
            } or document.get("decision_ref") != {"id": decision.get("event_id"), "sha256": decision.get("event_hash")}:
                raise IntegrityError("SPEC-01 correction does not bind the exact scorecard and owner decision")
            _verify_source_correction_remote(
                document,
                resolve_tag=_resolve_remote_tag,
                verify_paths=_verify_remote_commit_paths,
            )
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
            or document.get("registrar", {}).get("actor_id")
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
            spec_execution_authority_validator_factory=self._runtime().spec_execution_authority_validator,
            clock=self.operator.clock,
        )
        self._prepare_action_journal(action, packet, publish=True)
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
            spec_execution_authority_validator_factory=self._runtime().spec_execution_authority_validator,
            governing_evidence_resolver=GoverningScientificReviewStore(
                ObjectStore(self.operator.control_root), self.operator.schemas
            ),
            clock=self.operator.clock,
        )
        route_source = next(item for item in self.route["sources"] if item["alias"] == stage)
        _events, projection, _documents = self._snapshot()
        input_states = self._brief_input_states(projection)
        spec_rows = [
            state
            for state in input_states.values()
            if state["manifest"]["artefact_type"] == "spec_operator_source"
            and state.get("content_sha256") == route_source["sha256"]
        ]
        method_rows = [
            state
            for state in input_states.values()
            if state["manifest"]["artefact_type"] == "methods_asset"
            and state["manifest"].get("authority", {}).get("accepted_scope") == semantic["scope"]
        ]
        if len(spec_rows) != 1 or not method_rows:
            raise IntegrityError(f"{stage} accepted brief inputs are not exact")
        methods_pack = load_methods_pack(self.operator.repository_root)
        assets = []
        for state in method_rows:
            manifest = state["manifest"]
            raw = read_contained_regular_file(
                self.operator.control_root,
                manifest["relative_path"],
                label="registered SPEC artefact",
            )
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
        context_id = derive_spec_owner_context_id(
            actor_id=str(actor_id),
            operator_session_id=str(semantic["operator_session_id"]),
            recipient_id=str(semantic["recipient_id"]),
            purpose=str(semantic["purpose"]),
            scope=str(semantic["scope"]),
            application_version=str(semantic["application_version"]),
            valid_from=str(semantic["evaluation_time"]),
            expires_at=str(semantic["handoff_expires_at"]),
            retry_identity=str(packet["retry_id"]),
        )
        trusted_now = self._trusted_now()
        context_exists = any(event.get("stream_id") == context_id for event in _events)
        if not context_exists:
            for command_type in (
                "RequestContextPacket",
                "BeginContextCompilation",
                "CompleteContextCompilation",
                "PrepareOwnerOperatedContextHandoff",
                "ValidateOwnerOperatedContextHandoff",
                "IssueOwnerOperatedContextHandoff",
                "RecordOwnerOperatedContextDelivery",
            ):
                self._prevalidate_lifecycle_grant(
                    grant_id=str(registrations["context_authority_grant_id"]),
                    actor_id=str(actor_id),
                    command_type=command_type,
                    subject_kind="context",
                    subject_id=context_id,
                    now=trusted_now,
                )
        for registration_key in ("brief_registration", "package_registration"):
            registration = registrations[registration_key]
            if str(registration["artefact_id"]) in projection.get("artefact_streams", {}):
                continue
            self._prevalidate_lifecycle_grant(
                grant_id=str(registration["authority_grant_id"]),
                actor_id=str(actor_id),
                command_type="RegisterArtefact",
                subject_kind="artefact",
                subject_id=str(registration["artefact_id"]),
                now=trusted_now,
            )
        current = self.operator.ledger.snapshot()
        if current.events != _events:
            raise ConflictError("Discovery ledger changed during SPEC preparation preflight")
        self._prepare_action_journal(action, packet, publish=True)
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
            required_spec_source_sha256=str(route_source["sha256"]),
            projection_for_events=self._runtime().replay,
            dossier_id=self._dossier_id,
            candidate_scope_for_snapshot=lambda snapshot_events, snapshot_projection: self._route_census(
                snapshot_events, snapshot_projection
            ).candidate_ids,
        )
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
                spec_execution_authority_validator_factory=self._runtime().spec_execution_authority_validator,
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
            "document_type": str(_ACTION_DEFINITIONS[action].document_type),
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
        result = self._register_document(action, packet, package, registrations["package_registration"])
        return {"registration": result, "context_id": compiled.context_id, "brief": package}

    def advance(self, action: str, packet_path: Path) -> dict[str, Any]:
        """Advance one public SPEC action through its authoritative seam."""

        # Every public SPEC action may make several independently durable
        # writes before its completion identity.  Hold one recoverable fence
        # over the whole action so neither a context/brief/package preparation
        # nor a raw-registration/review batch can bind a stale Discovery tail.
        # Nested CommandService and DiscoveryRuntime submissions re-enter it.
        with SpecPreparationFence(self.operator.control_root):
            return self._advance_unfenced(action, packet_path)

    def _advance_unfenced(self, action: str, packet_path: Path) -> dict[str, Any]:
        packet = self._canonical_packet(packet_path)
        if packet.get("action") != action:
            raise IntegrityError("SPEC action argument and packet differ")
        definition = _ACTION_DEFINITIONS.get(action)
        if definition is None:
            raise IntegrityError("SPEC action is not registered")
        self._action_identity(action, packet, publish=False)
        prepared_action_exists = self._prepare_action_journal(action, packet, publish=False)
        events, projection, documents = self._snapshot()
        status = self._status_from_snapshot(events, projection, documents)
        accepted_actions = {
            definition.action
            for definition in _ACTION_DEFINITIONS.values()
            if definition.next_action == status.next_action
        }
        census = self._route_census(events, projection)
        completed_rows = set(census.rows)
        expected_document = definition.document_type
        action_state = self._action_state(
            action,
            completed_rows=completed_rows,
            documents=documents,
            projection=projection,
            events=events,
            prepared=prepared_action_exists,
        )
        if action not in accepted_actions and action_state.phase == "not_started":
            raise IntegrityError(f"SPEC action is not next; exact next action is {status.next_action}")
        if action_state.effects_complete and expected_document is not None:
            result = self._validate_completed_document_retry(action, packet, events, projection, documents)
            return self._complete_action(action, packet, result)
        if action_state.effects_complete and definition.brief_input_state is not None:
            result = self._completed_brief_input_result(action, packet, projection)
            return self._complete_action(action, packet, result)
        brief_input_action = action in {
            "register_spec_01_brief_inputs",
            "review_spec_01_brief_inputs",
            "accept_spec_01_brief_inputs",
        }
        commands = [] if brief_input_action else self._validate_commands(action, packet["commands"], completed_rows)
        self._validate_roles(commands, census)
        document_required = expected_document is not None
        if action == "register_spec_01_brief_inputs":
            if packet.get("document") is not None or not isinstance(packet.get("registration"), dict):
                raise IntegrityError("SPEC brief-input registration packet is malformed")
            entries = packet["registration"].get("raw_publications")
            if not isinstance(entries, list) or len(entries) != len(_BRIEF_INPUT_SOURCE_TYPES) or packet["commands"]:
                raise IntegrityError("SPEC brief-input registrations are incomplete")
            service = CommandService(
                self.operator.control_root,
                self.operator.ledger,
                ObjectStore(self.operator.control_root),
                ReceiptStore(self.operator.control_root),
                self.operator.schemas,
                authority_resolver=self.operator.authority_resolver,
                spec_execution_authority_validator_factory=self._runtime().spec_execution_authority_validator,
                clock=self.operator.clock,
            )
            expected_census = self._expected_brief_input_census()
            prepared_entries = []
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) != {"publication", "registration"}:
                    raise IntegrityError("SPEC brief-input registration entry is malformed")
                try:
                    publication = RawContentPublication(**entry["publication"])
                    registration = CandidateRegistration(**entry["registration"])
                except (TypeError, ValueError) as exc:
                    raise IntegrityError("SPEC brief-input registration entry is malformed") from exc
                if _BRIEF_INPUT_SOURCE_TYPES.get(publication.source_relative_path) != publication.document_type:
                    raise IntegrityError("SPEC brief-input registrations are not the exact required set")
                prepared = prepare_registered_raw_content(
                    repository_root=self.operator.repository_root,
                    publication=publication,
                    registration=registration,
                    control_root=self.operator.control_root,
                )
                expected = expected_census.get(registration.artefact_id)
                if expected is None or any(
                    actual != expected[key]
                    for key, actual in {
                        "artefact_id": registration.artefact_id,
                        "artefact_type": publication.document_type,
                        "source_relative_path": publication.source_relative_path,
                        "relative_path": publication.destination_relative_path,
                        "content_sha256": publication.content_sha256,
                        "size_bytes": publication.size_bytes,
                        "media_type": publication.media_type,
                    }.items()
                ):
                    raise IntegrityError("SPEC brief-input registration differs from the exact route census")
                prepared_entries.append(prepared)
            if {item.publication.source_relative_path for item in prepared_entries} != set(
                _BRIEF_INPUT_SOURCE_TYPES
            ) or {item.registration.artefact_id for item in prepared_entries} != set(expected_census):
                raise IntegrityError("SPEC brief-input registrations are not the exact required set")
            service.prevalidate_register_artefact_batch([item.command for item in prepared_entries])
            self._prepare_action_journal(action, packet, publish=True)
            registrations = []
            for item in prepared_entries:
                registered = publish_registered_raw_content(
                    repository_root=self.operator.repository_root,
                    publication=item.publication,
                    registration=item.registration,
                    control_root=self.operator.control_root,
                    command_service=service,
                )
                registrations.append(
                    {"artefact_id": registered.artefact_id, "content_sha256": registered.content_sha256}
                )
            return self._complete_action(
                action,
                packet,
                {
                    "route_id": ROUTE_ID,
                    "action": action,
                    "retry_id": packet["retry_id"],
                    "registration": registrations,
                    "receipts": [],
                    "status": asdict(self.status()),
                },
            )
        if action in {"review_spec_01_brief_inputs", "accept_spec_01_brief_inputs"}:
            review_publications = packet.get("registration")
            if packet.get("document") is not None or (
                action == "accept_spec_01_brief_inputs" and review_publications is not None
            ):
                raise IntegrityError("SPEC brief-input authority action cannot register a document")
            _events, projection, _documents = self._snapshot()
            expected_type = "RecordScientificReview" if action.startswith("review_") else "SetArtefactUseAuthority"
            all_inputs = self._brief_input_states(projection)
            pending_inputs = self._pending_brief_input_authority_states(projection, expected_type)
            command_targets = [
                envelope.get("target_stream_id") if isinstance(envelope, dict) else None
                for envelope in packet["commands"]
            ]
            command_ids = [
                envelope.get("command_id") if isinstance(envelope, dict) else None for envelope in packet["commands"]
            ]
            idempotency_keys = [
                envelope.get("idempotency_key") if isinstance(envelope, dict) else None
                for envelope in packet["commands"]
            ]
            if (
                len(command_targets) != len(set(command_targets))
                or len(command_ids) != len(set(command_ids))
                or len(idempotency_keys) != len(set(idempotency_keys))
                or any(not isinstance(value, str) or not value for value in command_ids + idempotency_keys)
                or not set(pending_inputs).issubset(command_targets)
                or any(target not in all_inputs for target in command_targets)
            ):
                raise IntegrityError("SPEC brief-input authority commands are incomplete")
            receipt_store = ReceiptStore(self.operator.control_root)
            for envelope, target in zip(packet["commands"], command_targets, strict=True):
                if target in pending_inputs:
                    continue
                receipt = receipt_store.load(str(envelope.get("command_id")))
                if receipt is None or receipt.status != "accepted":
                    raise IntegrityError("SPEC brief-input authority commands are incomplete")
            inputs = {str(target): all_inputs[str(target)] for target in command_targets}
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
                reference_ids = [
                    publication.get("reference_id") if isinstance(publication, dict) else None
                    for publication in publications
                ]
                review_ids = [
                    publication.get("record", {}).get("review_id")
                    if isinstance(publication, dict) and isinstance(publication.get("record"), dict)
                    else None
                    for publication in publications
                ]
                if (
                    len(reference_ids) != len(set(reference_ids))
                    or len(review_ids) != len(set(review_ids))
                    or any(not isinstance(value, str) or not value for value in reference_ids + review_ids)
                ):
                    raise IntegrityError("SPEC brief-input governing review identities are not unique")
            else:
                publications = []
            evaluation_time = self._trusted_now()
            service = CommandService(
                self.operator.control_root,
                self.operator.ledger,
                ObjectStore(self.operator.control_root),
                receipt_store,
                self.operator.schemas,
                authority_resolver=self.operator.authority_resolver,
                spec_execution_authority_validator_factory=self._runtime().spec_execution_authority_validator,
                governing_evidence_resolver=review_store,
                clock=self.operator.clock,
            )
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
                        or publication["record"].get("project_id") != self.operator.ledger.project_id
                        or publication["record"].get("review_id") != payload.get("review_id")
                        or publication["record"].get("subject_sha256") != state.get("content_sha256")
                        or publication["record"].get("reviewer_actor_id") != envelope.get("actor_id")
                    ):
                        raise IntegrityError("SPEC brief-input governing review binding differs")
            service.prevalidate_artefact_authority_batch(packet["commands"])
            review_store.prevalidate_publications(publications)
            self._prepare_action_journal(action, packet, publish=True)
            review_store.publish_batch(
                publications,
                project_id=self.operator.ledger.project_id,
                evaluation_time=evaluation_time,
            )
            receipts = [asdict(service.submit(deepcopy(envelope))) for envelope in packet["commands"]]
            return self._complete_action(
                action,
                packet,
                {
                    "route_id": ROUTE_ID,
                    "action": action,
                    "retry_id": packet["retry_id"],
                    "registration": None,
                    "receipts": receipts,
                    "status": asdict(self.status()),
                },
            )
        if action in {"prepare_spec_01", "prepare_spec_02"}:
            if packet["commands"]:
                raise IntegrityError("SPEC preparation cannot submit a Discovery route command")
            prepared = self._prepare_spec("SPEC-01" if action == "prepare_spec_01" else "SPEC-02", packet)
            return self._complete_action(
                action,
                packet,
                {
                    "route_id": ROUTE_ID,
                    "action": action,
                    "retry_id": packet["retry_id"],
                    **prepared,
                    "receipts": [],
                    "status": asdict(self.status()),
                },
            )
        if document_required != (packet.get("document") is not None and packet.get("registration") is not None):
            raise IntegrityError("SPEC action document/registration presence differs")
        if not document_required and (packet.get("document") is not None or packet.get("registration") is not None):
            raise IntegrityError("SPEC command-only action cannot register a document")
        registration_result = None
        for command in commands:
            self.operator.prevalidate(
                command,
                prospective_document=packet["document"] if document_required else None,
            )
        if document_required:
            registration_result = self._register_document(
                action,
                packet,
                packet["document"],
                packet["registration"],
                commands,
            )
        receipts = [asdict(self.operator.submit(command)) for command in commands]
        return self._complete_action(
            action,
            packet,
            {
                "route_id": ROUTE_ID,
                "action": action,
                "retry_id": packet["retry_id"],
                "registration": registration_result,
                "receipts": receipts,
                "status": asdict(self.status()),
            },
        )


__all__ = ["ROUTE_ID", "SpecFlow", "SpecFlowStatus", "build_spec_authority_subject"]
