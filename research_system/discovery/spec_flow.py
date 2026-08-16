"""Provider-free operator coordinator for the governed Gate 6 SPEC route.

The coordinator owns no research execution and no second lifecycle state
machine.  Durable lifecycle truth is replayed from the Discovery ledger; an
advance packet merely supplies the real identities, authority references, and
evidence required by the one next route action.
"""

from __future__ import annotations

import json
import tempfile
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
from research_system.discovery.routes import discovery_route
from research_system.discovery.runtime import DiscoveryRuntime
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system.git_execution import run_git
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    RawContentPublication,
    prepare_candidate_document,
    prepare_registered_raw_content,
    publish_registered_raw_content,
    register_candidate_document,
)
from research_system.evidence.consumers import ArtefactEvidenceConsumers
from research_system.methods.brief import export_brief
from research_system.methods.pack import load_methods_pack
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from research_system.store.spec_preparation_fence import SpecPreparationFence


ROUTE_ID = "SPEC-GATE6-RUN-V1"
_ROUTE_PATH = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json")
_SPEC_01_PATH = _ROUTE_PATH.parent / "spec-01-assay-brief-v1.1.0.md"
_SPEC_02_PATH = _ROUTE_PATH.parent / "spec-02-micro-spike-contract-v1.1.0.md"
_DOSSIER_AUTHORITY_PATH = _ROUTE_PATH.parent / "spec-dossier-expected-set-authority.json"
_PATH_AUTHORITY_PATH = _ROUTE_PATH.parent / "spec-path-registration-authority.json"
_DOSSIER_MANIFEST_PATH = _ROUTE_PATH.parent / "spec-research-dossier-manifest.json"
_REGISTERED_PATH_POLICY_PATH = _ROUTE_PATH.parent / "registered-path-read-policy.json"
_P042_DECISION_PATH = Path("docs/plans/agentic-research-system/03-decisions-and-open-questions.md")
_P042_HEADING = b"### P-042 - Owner-operated external model sessions"
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
    "correct_spec_01_source": "ars://portfolio/spec-01-source-correction",
    "approve_spec_02": "ars://portfolio/spec-02-live-run-approval",
    "prepare_spec_02": "ars://portfolio/spec-operator-brief-package",
    "return_spec_02_complete": "ars://portfolio/spec-operator-return",
    "return_spec_02_partial": "ars://portfolio/spec-operator-return",
}
_DOCUMENT_TYPES = {
    "prepare_spec_01": "spec_01_operator_brief",
    "return_spec_01_complete": "spec_01_return",
    "return_spec_01_partial": "spec_01_return",
    "correct_spec_01_source": "spec_01_source_correction",
    "approve_spec_02": "spec_02_live_run_approval",
    "prepare_spec_02": "spec_02_operator_brief",
    "return_spec_02_complete": "spec_02_return",
    "return_spec_02_partial": "spec_02_return",
}
_BRIEF_INPUT_TYPES = {"spec_operator_source", "methods_asset"}
_BRIEF_INPUT_SOURCE_TYPES = {
    _SPEC_01_PATH.as_posix(): "spec_operator_source",
    _SPEC_02_PATH.as_posix(): "spec_operator_source",
    ".research-system/methods/assets/adversarial-review-protocol.md": "methods_asset",
}
_SINGLE_SHOT_ACTIONS = frozenset(_DOCUMENT_ACTION_SCHEMA) | frozenset(
    {
        "register_spec_01_brief_inputs",
        "review_spec_01_brief_inputs",
        "accept_spec_01_brief_inputs",
    }
)


@dataclass(frozen=True)
class SpecFlowStatus:
    capability_state: str
    completed_stage: str
    next_action: str | None
    block_reason: str | None
    route_id: str = ROUTE_ID


def _git(repository_root: Path, *arguments: str) -> str:
    result = run_git(
        repository_root,
        *arguments,
        unavailable_message="SPEC route Git validation is unavailable",
    )
    if result.returncode != 0:
        raise ConfigurationError("SPEC route is not committed at operator HEAD")
    return result.stdout.strip()


def _resolve_remote_tag(repository_url: str, resolved_ref: str) -> str:
    """Resolve one exact remote tag without treating the heads namespace as exhaustive."""

    try:
        with tempfile.TemporaryDirectory(prefix="ars-spec-ls-remote-") as directory:
            result = run_git(
                Path(directory),
                "ls-remote",
                "--tags",
                repository_url,
                resolved_ref,
                timeout=30,
                unavailable_message="SPEC-01 correction remote reference could not be resolved",
            )
    except ConfigurationError as exc:
        raise IntegrityError("SPEC-01 correction remote reference could not be resolved") from exc
    lines = [line.split() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or len(lines) != 1 or len(lines[0]) != 2 or lines[0][1] != resolved_ref:
        raise IntegrityError("SPEC-01 correction remote tag resolution is not exact")
    return lines[0][0]


def _verify_remote_commit_paths(
    repository_url: str,
    resolved_ref: str,
    commit_oid: str,
    required_paths: Sequence[Mapping[str, Any]],
) -> None:
    """Verify every correction path against bytes fetched from the pinned remote ref."""

    if not isinstance(repository_url, str) or not isinstance(resolved_ref, str):
        raise IntegrityError("SPEC-01 correction remote identity is invalid")
    if not isinstance(commit_oid, str) or len(commit_oid) != 40:
        raise IntegrityError("SPEC-01 correction commit identity is invalid")
    if not required_paths:
        raise IntegrityError("SPEC-01 correction required paths are empty")
    expected: dict[str, str] = {}
    for item in required_paths:
        path = item.get("path") if isinstance(item, Mapping) else None
        digest = item.get("sha256") if isinstance(item, Mapping) else None
        relative = Path(path) if isinstance(path, str) else None
        if (
            relative is None
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != path
            or not isinstance(digest, str)
            or len(digest) != 64
            or path in expected
        ):
            raise IntegrityError("SPEC-01 correction required path binding is invalid")
        expected[path] = digest
    try:
        with tempfile.TemporaryDirectory(prefix="ars-spec-correction-") as directory:
            checkout = Path(directory)
            commands = (("init", "--quiet"), ("remote", "add", "origin", repository_url))
            for arguments in commands:
                result = run_git(
                    checkout,
                    *arguments,
                    timeout=30,
                    text=False,
                    unavailable_message="SPEC-01 correction remote content could not be fetched",
                )
                if result.returncode != 0:
                    raise IntegrityError("SPEC-01 correction remote content could not be fetched")
            fetched = run_git(
                checkout,
                "fetch",
                "--quiet",
                "--depth=1",
                "origin",
                resolved_ref,
                timeout=30,
                unavailable_message="SPEC-01 correction remote content could not be fetched",
            )
            if fetched.returncode != 0:
                raise IntegrityError("SPEC-01 correction remote content could not be fetched")
            resolved = run_git(
                checkout,
                "rev-parse",
                "FETCH_HEAD^{commit}",
                timeout=30,
                unavailable_message="SPEC-01 correction fetched ref could not be resolved",
            )
            if resolved.returncode != 0 or resolved.stdout.strip() != commit_oid:
                raise IntegrityError("SPEC-01 correction fetched ref differs from its pinned commit")
            for path, digest in expected.items():
                content = run_git(
                    checkout,
                    "show",
                    f"{commit_oid}:{path}",
                    text=False,
                    timeout=30,
                    unavailable_message="SPEC-01 correction remote path could not be read",
                )
                if content.returncode != 0 or sha256_hex(content.stdout) != digest:
                    raise IntegrityError("SPEC-01 correction required path differs from the pinned commit")
    except ConfigurationError as exc:
        raise IntegrityError("SPEC-01 correction remote content could not be verified") from exc


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
        if isinstance(assay_authority, Mapping):
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
        try:
            raw = read_contained_regular_file(
                operator.control_root,
                relative,
                label="registered SPEC document",
            )
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
    if len(actors) > 1:
        raise IntegrityError(f"multiple actors are bound to route row {row}")
    return next(iter(actors)) if actors else None


class SpecFlow:
    """One stage-aware, provider-free SPEC route coordinator."""

    def __init__(self, operator: DiscoveryOperator) -> None:
        self.operator = operator
        self.route = _validate_route(operator)

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
        projection = self._runtime().replay(events)
        documents = _registered_documents(self.operator, projection)
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

    def _action_identity(self, action: str, packet: Mapping[str, Any], *, publish: bool) -> bool:
        if action not in _SINGLE_SHOT_ACTIONS:
            return False
        value = {
            "schema_id": "ars://internal/spec-flow-action-identity",
            "schema_version": "1.0.0",
            "route_id": ROUTE_ID,
            "action": action,
            "retry_id": packet.get("retry_id"),
            "packet_sha256": sha256_hex(canonical_bytes(packet)),
        }
        store = CandidateDocumentStore(
            self.operator.control_root,
            relative_directory=Path("runtime/spec-flow-actions"),
        )
        relative = store.relative_path(action)
        target = self.operator.control_root / relative
        if target.exists() or target.is_symlink():
            raw = read_contained_regular_file(
                self.operator.control_root,
                relative,
                label="SPEC action retry identity",
            )
            if raw != canonical_bytes(value):
                raise ConflictError("completed SPEC action retry differs from its durable packet")
            return True
        if publish:
            store.publish_bytes(action, canonical_bytes(value))
        return False

    def _complete_action(self, action: str, packet: Mapping[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        self._action_identity(action, packet, publish=True)
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
    ) -> None:
        document_type = _DOCUMENT_TYPES[action]
        durable = documents.get(document_type, ())
        if len(durable) != 1:
            raise IntegrityError("completed SPEC document action has no exact durable document")
        stream_rows = [
            (str(stream_id), state)
            for stream_id, state in projection.get("artefact_streams", {}).items()
            if isinstance(state, Mapping)
            and isinstance(state.get("manifest"), Mapping)
            and state["manifest"].get("artefact_type") == document_type
        ]
        if len(stream_rows) != 1:
            raise IntegrityError("completed SPEC document action has no exact durable registration")
        package_id, _state = stream_rows[0]
        registrations = packet.get("registration")
        supplied_document = packet.get("document")
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
            registration = registrations.get("package_registration")
            brief_registration = registrations.get("brief_registration")
            if (
                not isinstance(registration, dict)
                or not isinstance(brief_registration, dict)
                or registration.get("artefact_id") != package_id
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

    @staticmethod
    def _brief_input_states(projection: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        return {
            str(stream_id): state
            for stream_id, state in projection.get("artefact_streams", {}).items()
            if isinstance(state, Mapping)
            and isinstance(state.get("manifest"), Mapping)
            and state["manifest"].get("artefact_type") in _BRIEF_INPUT_TYPES
            and isinstance(state["manifest"].get("authority"), Mapping)
            and state["manifest"].get("authority", {}).get("accepted_scope") == "spec-gate6-run"
        }

    @classmethod
    def _pending_brief_input_authority_states(
        cls, projection: Mapping[str, Any], command_type: str
    ) -> dict[str, Mapping[str, Any]]:
        inputs = cls._brief_input_states(projection)
        if command_type == "RecordScientificReview":
            return {stream_id: state for stream_id, state in inputs.items() if not state.get("scientific_reviews")}
        if command_type == "SetArtefactUseAuthority":
            return {
                stream_id: state
                for stream_id, state in inputs.items()
                if state.get("use_authority") != "accepted_for_scope"
            }
        raise IntegrityError("SPEC brief-input authority command type is unsupported")

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
        required_source_hashes = [
            source["sha256"] for source in self.route["sources"] if source["alias"] in {"SPEC-01", "SPEC-02"}
        ]
        required_hashes = sorted(
            required_source_hashes
            + [
                sha256_hex((self.operator.repository_root / path).read_bytes())
                for path, kind in _BRIEF_INPUT_SOURCE_TYPES.items()
                if kind == "methods_asset"
            ]
        )
        registered_hashes = sorted(state.get("content_sha256") for state in brief_inputs.values())
        if registered_hashes != required_hashes:
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
        if candidate_status == "killed":
            return SpecFlowStatus("PROVEN", "spec_01_killed", None, "owner decision KILLED is terminal")
        correction = documents.get("spec_01_source_correction", ())
        approval = documents.get("spec_02_live_run_approval", ())
        if candidate_status == "parked" and not correction:
            return SpecFlowStatus(
                "NOT_RUNNABLE",
                "spec_01_parked",
                "correct_spec_01_source",
                "the recorded paper-code availability finding must be corrected before any later test",
            )
        if candidate_status == "parked" and not approval:
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
        if not approval:
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

    def _register_document(
        self,
        action: str,
        document: Any,
        registration: Any,
        commands: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
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
        if (
            isinstance(registration, dict)
            and set(registration) == _REGISTRATION_FIELDS
            and isinstance(registration.get("manifest"), dict)
            and registration["manifest"].get("artefact_type") != document["document_type"]
        ):
            raise IntegrityError("SPEC document registration type differs from its validated document")
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
        if action == "approve_spec_02":
            events = tuple(self.operator.ledger.iter_events())
            owner_actor = _actor_for_row(events, "OR-013")
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
            assays = [value for value in projection.get("assays", {}).values() if isinstance(value, Mapping)]
            decisions = [
                event
                for event in events
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
            git_ref = document.get("corrected_git_reference", {})
            if _resolve_remote_tag(git_ref.get("repository_url"), git_ref.get("resolved_ref")) != git_ref.get(
                "commit_oid"
            ):
                raise IntegrityError("SPEC-01 correction commit differs from the live remote tag")
            _verify_remote_commit_paths(
                git_ref.get("repository_url"),
                git_ref.get("resolved_ref"),
                git_ref.get("commit_oid"),
                git_ref.get("required_paths"),
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
        action_identity_exists = self._action_identity(action, packet, publish=False)
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
        if already_completed and expected_document is not None:
            if not action_identity_exists:
                self._validate_completed_document_retry(action, packet, events, _projection, documents)
                self._action_identity(action, packet, publish=True)
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
                prepared_entries.append(
                    prepare_registered_raw_content(
                        repository_root=self.operator.repository_root,
                        publication=publication,
                        registration=registration,
                        control_root=self.operator.control_root,
                    )
                )
            if (
                {item.publication.source_relative_path for item in prepared_entries} != set(_BRIEF_INPUT_SOURCE_TYPES)
                or len({item.registration.artefact_id for item in prepared_entries}) != len(prepared_entries)
                or len({item.publication.destination_relative_path for item in prepared_entries})
                != len(prepared_entries)
            ):
                raise IntegrityError("SPEC brief-input registrations are not the exact required set")
            service.prevalidate_register_artefact_batch([item.command for item in prepared_entries])
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
