from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping

from research_system.authority import GrantedCommandIdentity, LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command, Receipt
from research_system.command.reducers import reduce_artefact, replay_control_plane
from research_system.discovery.authority import (
    PORTABLE_SPEC_REQUIRED_MEMBERS,
    is_portable_path_subject,
    prepare_authority_transition,
    validate_portable_path_subject,
)
from research_system.discovery.assay_authority import (
    content_sha256 as assay_content_sha256,
    replay_assay_bar_authority,
)
from research_system.discovery.assay_successor import (
    prevalidate_assay_authority_successor_remote,
    successor_document_hashes,
    validate_assay_authority_successor_document,
)
from research_system.discovery.source_correction import SourceCorrectionRemoteProof
from research_system.discovery.accepted_w11 import (
    ACCEPTED as _ACCEPTED,
    CATALOGUE_STREAM_ID as _CATALOGUE_STREAM_ID,
    ROW_IDS as _ROW_IDS,
    accepted_genesis_payload as _accepted_genesis_payload,
)
from research_system.discovery.routes import (
    DISCOVERY_EXISTING_TARGETS as _DISCOVERY_EXISTING_TARGETS,
    DISCOVERY_IDENTITY_COLLECTIONS as _DISCOVERY_IDENTITY_COLLECTIONS,
    DISCOVERY_MINT_ROWS as _DISCOVERY_MINT_ROWS,
    discovery_identity_exists as _discovery_identity_exists,
    discovery_route as _discovery_route,
    shared_event_partition as _shared_event_partition,
    validate_discovery_route_registry as _validate_discovery_route_registry,
)
from research_system.discovery.rules import (
    _assay_cancellation_matches,
    _assay_partial_bindings_match,
    _assay_scorecard_matches,
    _assay_staleness_matches,
    _candidate_ref,
    _candidate_replacement_is_used,
    _candidate_supersession_lineage,
    _git_blob,
    _is_spec_route_candidate,
    _promotion_relation_matches,
    _parked_candidate_test_plan_matches,
    _record_ref,
    _review_policy_status,
    _revisit_relation_matches,
    _source_observation_multiset_hash,
    _spike_cancellation_matches,
    _spike_execution_ids_available,
    _spike_execution_relation_matches,
    _spike_plan_matches,
    _spike_verdict_matches,
    _valid_promotion_options,
    _valid_review_supersession,
    _valid_revisit_proposal,
    _valid_spike_execution_proposal,
    _valid_spike_promotion_option,
)
from research_system.discovery.path_safety import read_contained_regular_file
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.replay.transactions import validate_prepared_transaction_contract
from research_system.discovery.commands import (
    DISCOVERY_COMMAND_TYPES,
    discovery_resolve_transaction_ids,
)
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierAdmissionRejected,
    DossierMember,
    RegisteredRoot,
    prepare_dossier_admission,
    registered_root_identity_hash,
)
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system.git_execution import run_git
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.lock import CompositeWriterLock, WriterLock
from research_system.store.receipts import ReceiptStore
from research_system.store.spec_preparation_fence import SpecPreparationFence


_COMMAND_FIELDS = {
    "command_id",
    "command_type",
    "actor_id",
    "authority_grant_id",
    "idempotency_key",
    "target_stream_id",
    "expected_stream_version",
    "payload",
}
_GIT_TIMEOUT_SECONDS = 10
_SPEC_02_APPROVAL_AUTHORITY_REASON = "Authorize exact governed publication of the owner-approved SPEC-02 run decision."
_SPEC_02_APPROVAL_EVIDENCE_PREFIX = "spec-02-approval-sha256:"
_SPEC_02_GATED_TRANSITIONS = frozenset(
    {
        ("RegisterSpikePlan", "OR-014"),
        ("ProposeSpikeExecutionDecision", "OR-015"),
        ("ResolveDecision", "OR-016"),
        ("StartSpike", "OR-017"),
        ("RecordSpikeVerdict", "OR-018"),
        ("RecordSpikeVerdict", "OR-019"),
    }
)


@dataclass(frozen=True)
class _Spec02ExecutionAuthority:
    approval: Mapping[str, Any]
    brief: Mapping[str, Any]
    correction: Mapping[str, Any] | None


def _exact_record_ref_matches(value: object, record_id: str, content_hash: str) -> bool:
    """Match one exact revision-1 record reference without accepting aliases."""

    return value == {"id": record_id, "record_revision": 1, "content_hash": content_hash}


def _exact_source_ref_matches(value: object, record_id: str, content_hash: str) -> bool:
    """Match one exact revision-1 artefact source reference."""

    return value == {
        "ref_kind": "artefact",
        "id": record_id,
        "record_revision": 1,
        "content_hash": content_hash,
    }


def _one_exact_ref(values: object, record_id: str, predicate: Callable[[object], bool]) -> bool:
    """Require the sole reference for one governed identity to match exactly."""

    if not isinstance(values, list):
        return False
    matching_identity = [value for value in values if isinstance(value, Mapping) and value.get("id") == record_id]
    return len(matching_identity) == 1 and predicate(matching_identity[0])


def _assay_content_matches_current_spec_sources(
    content: object,
    *,
    kind: str,
    route_sha256: str,
    spec_01_sha256: str,
) -> bool:
    """Bind new Assay authority writes to the current committed SPEC route."""

    if not isinstance(content, Mapping):
        return False
    source_refs = content.get("source_refs")
    if not (
        _one_exact_ref(
            source_refs,
            "SPEC-01",
            lambda value: _exact_source_ref_matches(value, "SPEC-01", spec_01_sha256),
        )
        and _one_exact_ref(
            source_refs,
            "SPEC-GATE6-RUN-V1",
            lambda value: _exact_source_ref_matches(value, "SPEC-GATE6-RUN-V1", route_sha256),
        )
        and _exact_record_ref_matches(
            content.get("effective_project_scope_ref"),
            "prj_01978abc-1000-7000-8000-000000001000",
            route_sha256,
        )
    ):
        return False
    if kind == "scope":
        return True
    authority_refs = content.get("source_authority_refs")
    return _one_exact_ref(
        authority_refs,
        "SPEC-01",
        lambda value: _exact_record_ref_matches(value, "SPEC-01", spec_01_sha256),
    ) and _one_exact_ref(
        authority_refs,
        "SPEC-GATE6-RUN-V1",
        lambda value: _exact_record_ref_matches(value, "SPEC-GATE6-RUN-V1", route_sha256),
    )


def _spec_02_plan_contract_matches(plan: object, authority: _Spec02ExecutionAuthority) -> bool:
    """Bind the OR-014 plan to the exact owner-governed SPEC-02 source."""

    subject = authority.approval.get("spec_02_subject")
    source = authority.brief.get("route_source")
    if not isinstance(plan, Mapping) or not isinstance(subject, Mapping) or not isinstance(source, Mapping):
        return False
    source_sha256 = source.get("raw_sha256")
    planned_contracts = plan.get("planned_contracts")
    return bool(
        subject == {"id": "SPEC-02", "sha256": source_sha256}
        and isinstance(source_sha256, str)
        and len(source_sha256) == 64
        and isinstance(planned_contracts, list)
        and f"SPEC-02:{source_sha256}" in planned_contracts
    )


def _spec_02_pass_rerun_matches(document: object, payload: Mapping[str, Any]) -> bool:
    """Require a PASS return's rerun assertion to name its exact check evidence."""

    if payload.get("verdict") != "PASS":
        return True
    if not isinstance(document, Mapping):
        return False
    rerun = document.get("deterministic_rerun")
    artifact_hashes = document.get("artifact_hashes")
    if not isinstance(artifact_hashes, list):
        return False
    check_hashes = [
        item.get("sha256") for item in artifact_hashes if isinstance(item, Mapping) and item.get("name") == "checks"
    ]
    return bool(
        isinstance(rerun, Mapping)
        and rerun.get("performed") is True
        and rerun.get("same_output") is True
        and len(check_hashes) == 1
        and rerun.get("evidence_sha256") == check_hashes[0]
    )


class _SpecExecutionAuthorityResolver:
    """Resolve immutable SPEC execution authority without operator-only configuration."""

    def __init__(
        self,
        *,
        control_root: Path,
        schemas: SchemaRegistry,
        authority_resolver: LedgerAuthorityGrantResolver,
        clock: Callable[[], datetime],
    ) -> None:
        self.control_root = control_root
        self.schemas = schemas
        self.authority_resolver = authority_resolver
        self.clock = clock

    def _authority_decision_context(
        self,
        projection: Mapping[str, Any],
        events: tuple[dict[str, Any], ...],
    ) -> tuple[object, tuple[dict[str, Any], ...]]:
        """Load the verified owner anchor and its independently bound authority ledger."""

        if self.authority_resolver.control_root.resolve(strict=False) == self.control_root.resolve(strict=False):
            if not isinstance(projection, dict):
                raise IntegrityError("same-root SPEC authority projection is invalid")
            return self.authority_resolver._administration_context_from_projection(projection), events
        administration = self.authority_resolver.administration_context()
        events = (
            EventLedger(
                self.authority_resolver.control_root,
                self.authority_resolver.project_id,
                self.schemas,
                store_identity=self.authority_resolver.expected_store_identity,
            )
            .snapshot()
            .events
        )
        return administration, events

    def _has_authenticated_owner_approval_decision(
        self,
        *,
        approval: Mapping[str, Any],
        approval_sha256: str,
        approval_grant_id: object,
        approval_manifest: Mapping[str, Any],
        projection: Mapping[str, Any],
        events: tuple[dict[str, Any], ...],
    ) -> bool:
        """Bind approval bytes to the exact root-owner publication command."""

        registrar = approval.get("registrar")
        valid_window = approval.get("valid_window")
        artefact_id = approval_manifest.get("artefact_id")
        if (
            not isinstance(registrar, Mapping)
            or not isinstance(valid_window, Mapping)
            or not isinstance(artefact_id, str)
            or not isinstance(approval_grant_id, str)
        ):
            return False
        administration, authority_events = self._authority_decision_context(projection, events)
        intent = {
            "target_actor_id": registrar.get("actor_id"),
            "target_actor_class": "agent",
            "authority_lane": "producer/spec_brief_registration",
            "actor_role": "SPEC brief producer",
            "subject_scope": {
                "project_id": self.authority_resolver.project_id,
                "subject": {"kind": "artefact", "id": artefact_id},
            },
            "evidence_refs": [f"{_SPEC_02_APPROVAL_EVIDENCE_PREFIX}{approval_sha256}"],
            "effective_at": valid_window.get("starts_at"),
            "expires_at": valid_window.get("expires_at"),
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
                and event.get("actor_id") == getattr(administration, "owner_actor_id", None)
                and event.get("authority_grant_id") == getattr(administration, "root_grant_id", None)
                and event.get("command_payload_hash") == expected_payload_hash
                and isinstance(decision, Mapping)
                and decision.get("owner_actor_id") == getattr(administration, "owner_actor_id", None)
                and decision.get("target_grant_id") == approval_grant_id
                and decision.get("subject_scope") == intent["subject_scope"]
                and decision.get("effective_at") == intent["effective_at"]
                and decision.get("expires_at") == intent["expires_at"]
                and isinstance(proposed_grant, Mapping)
                and proposed_grant.get("authority_grant_id") == approval_grant_id
                and proposed_grant.get("actor_id") == registrar.get("actor_id")
                and proposed_grant.get("subject_scope") == intent["subject_scope"]
            ):
                matches.append(event)
        return len(matches) == 1

    def resolve(
        self,
        candidate: Mapping[str, Any],
        projection: Mapping[str, Any],
        *,
        events: tuple[dict[str, Any], ...],
        evaluation_time: datetime | None = None,
        owner_published_grant_ids: frozenset[str] | None = None,
    ) -> _Spec02ExecutionAuthority | None:
        """Resolve the durable approval and prepared brief for either SPEC-02 entry mode."""

        if not _is_spec_route_candidate(projection, candidate):
            return None
        if not isinstance(candidate.get("decision_id"), str):
            return None
        promotions = [
            event
            for event in events
            if event.get("event_type") == "CandidatePromotionApplied"
            and event.get("stream_id") == candidate.get("candidate_id")
            and event.get("payload", {}).get("row_id") == "OR-013"
        ]
        if len(promotions) != 1:
            return None
        promotion = promotions[0]
        documents: dict[str, list[tuple[dict[str, Any], str, object, object, Mapping[str, Any]]]] = {}
        for event in events:
            if event.get("event_type") != "ArtefactRegistered":
                continue
            manifest = event.get("payload", {}).get("manifest")
            if not isinstance(manifest, Mapping) or manifest.get("artefact_type") not in {
                "spec_01_source_correction",
                "spec_02_live_run_approval",
                "spec_02_operator_brief",
            }:
                continue
            relative = manifest.get("relative_path")
            content_sha256 = manifest.get("content_sha256")
            if not isinstance(relative, str) or not isinstance(content_sha256, str):
                return None
            try:
                raw = read_contained_regular_file(
                    self.control_root,
                    relative,
                    label="SPEC-02 approval artefact",
                )
                value = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return None
            if not isinstance(value, dict) or raw != canonical_bytes(value) or sha256_hex(raw) != content_sha256:
                return None
            documents.setdefault(str(manifest["artefact_type"]), []).append(
                (value, content_sha256, event.get("actor_id"), event.get("authority_grant_id"), manifest)
            )
        correction_rows = documents.get("spec_01_source_correction", [])
        approval_rows = documents.get("spec_02_live_run_approval", [])
        brief_rows = [row for row in documents.get("spec_02_operator_brief", []) if row[0].get("stage") == "SPEC-02"]
        if len(approval_rows) != 1 or len(brief_rows) != 1:
            return None
        approval, approval_sha256, approval_actor_id, approval_grant_id, approval_manifest = approval_rows[0]
        brief, _brief_sha256, brief_actor_id, _brief_grant_id, brief_manifest = brief_rows[0]
        try:
            self.schemas.validate(
                "ars://portfolio/spec-02-live-run-approval",
                approval,
                schema_version="1.0.0",
            )
            self.schemas.validate(
                "ars://portfolio/spec-operator-brief-package",
                brief,
                schema_version="1.0.0",
            )
            starts = datetime.fromisoformat(approval["valid_window"]["starts_at"].replace("Z", "+00:00"))
            expires = datetime.fromisoformat(approval["valid_window"]["expires_at"].replace("Z", "+00:00"))
            approved_at = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError, SchemaError):
            return None
        now = self.clock() if evaluation_time is None else evaluation_time
        route_source = brief.get("route_source", {})
        source_sha256 = route_source.get("raw_sha256") if isinstance(route_source, Mapping) else None
        source_path = route_source.get("relative_path") if isinstance(route_source, Mapping) else None
        owner = approval.get("owner", {})
        registrar = approval.get("registrar", {})
        common = bool(
            now.tzinfo is not None
            and now.utcoffset() is not None
            and starts <= now < expires
            and starts <= approved_at < expires
            and approved_at <= now
            and owner.get("actor_id") == promotion.get("actor_id")
            and registrar.get("actor_id") != owner.get("actor_id")
            and registrar.get("actor_id") == approval_actor_id
            and registrar.get("actor_id") == approval_manifest.get("producer_actor_id")
            and approval_grant_id
            in (
                self.authority_resolver.owner_published_grant_ids()
                if owner_published_grant_ids is None
                else owner_published_grant_ids
            )
            and self._has_authenticated_owner_approval_decision(
                approval=approval,
                approval_sha256=approval_sha256,
                approval_grant_id=approval_grant_id,
                approval_manifest=approval_manifest,
                projection=projection,
                events=events,
            )
            and brief.get("operator_session", {}).get("operator_actor_id") == brief_actor_id
            and brief_actor_id == brief_manifest.get("producer_actor_id")
            and approval.get("spec_01_promotion")
            == {"id": promotion.get("event_id"), "sha256": promotion.get("event_hash")}
            and approval.get("spec_02_subject") == {"id": "SPEC-02", "sha256": source_sha256}
            and approval.get("brief_identity") == {"id": source_path, "sha256": source_sha256}
        )
        if not common:
            return None
        selected = promotion.get("payload", {}).get("selected_option")
        if approval.get("entry_mode") == "standard_promotion":
            return (
                _Spec02ExecutionAuthority(approval=approval, brief=brief, correction=None)
                if (
                    selected == "PROMOTE"
                    and approval.get("scientific_promotion") is True
                    and approval.get("source_correction") is None
                    and not correction_rows
                )
                else None
            )
        if approval.get("entry_mode") != "owner_approved_park_test" or len(correction_rows) != 1:
            return None
        correction, correction_sha256, correction_actor_id, _correction_grant_id, correction_manifest = correction_rows[
            0
        ]
        try:
            self.schemas.validate(
                "ars://portfolio/spec-01-source-correction",
                correction,
                schema_version="1.0.0",
            )
        except SchemaError:
            return None
        return (
            _Spec02ExecutionAuthority(approval=approval, brief=brief, correction=correction)
            if (
                selected == "PARK"
                and approval.get("scientific_promotion") is False
                and approval.get("source_correction")
                == {"id": correction.get("correction_id"), "sha256": correction_sha256}
                and correction.get("decision_ref")
                == {"id": promotion.get("event_id"), "sha256": promotion.get("event_hash")}
                and correction.get("scientific_disposition") == "PARK"
                and correction.get("producer", {}).get("actor_id") == correction_actor_id
                and correction_actor_id == correction_manifest.get("producer_actor_id")
            )
            else None
        )


def build_spec_execution_authority_validator(
    *,
    control_root: Path,
    schemas: SchemaRegistry,
    authority_resolver: LedgerAuthorityGrantResolver,
    events: tuple[dict[str, Any], ...],
    clock: Callable[[], datetime] | None = None,
) -> Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], bool], None]:
    """Build strict external-document validation for one exact replay snapshot."""

    resolver = _SpecExecutionAuthorityResolver(
        control_root=control_root,
        schemas=schemas,
        authority_resolver=authority_resolver,
        clock=clock or (lambda: datetime.now(UTC)),
    )
    owner_published_grant_ids: frozenset[str] | None = None

    def validate_spec_authority(
        projection: Mapping[str, Any],
        candidate: Mapping[str, Any],
        event: Mapping[str, Any],
        park_test: bool,
    ) -> None:
        nonlocal owner_published_grant_ids
        occurred_at = event.get("occurred_at")
        try:
            evaluation_time = datetime.fromisoformat(str(occurred_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise IntegrityError("SPEC-02 transition lacks a valid occurrence time") from exc
        if evaluation_time.tzinfo is None or evaluation_time.utcoffset() is None:
            raise IntegrityError("SPEC-02 transition lacks a valid occurrence time")
        if owner_published_grant_ids is None:
            if authority_resolver.control_root.resolve(strict=False) == control_root.resolve(strict=False):
                publications = projection.get("owner_authority_decision_publications")
                if not isinstance(publications, Mapping):
                    raise IntegrityError("owner authority decision publication projection is invalid")
                owner_published_grant_ids = frozenset(
                    validate_id(str(publication.get("target_grant_id")), "authority_grant")
                    for publication in publications.values()
                    if isinstance(publication, Mapping)
                )
                if len(owner_published_grant_ids) != len(publications):
                    raise IntegrityError("owner authority decision publication projection is invalid")
            else:
                owner_published_grant_ids = authority_resolver.owner_published_grant_ids()
        authority = resolver.resolve(
            candidate,
            projection,
            events=events,
            evaluation_time=evaluation_time,
            owner_published_grant_ids=owner_published_grant_ids,
        )
        if authority is None or (authority.correction is not None) != park_test:
            raise IntegrityError("SPEC-02 execution lacks valid durable approval evidence")
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            raise IntegrityError("SPEC-02 transition payload is invalid")
        if event.get("command_type") == "RegisterSpikePlan" and payload.get("row_id") == "OR-014":
            if not _spec_02_plan_contract_matches(payload.get("plan_artifact"), authority):
                raise IntegrityError("SPEC-02 Spike plan differs from the exact governed contract")
        if (
            event.get("command_type") == "RecordSpikeVerdict"
            and payload.get("row_id") == "OR-018"
            and payload.get("verdict") == "PASS"
        ):
            returns: list[Mapping[str, Any]] = []
            for registered_event in events:
                if registered_event.get("event_type") != "ArtefactRegistered":
                    continue
                manifest = registered_event.get("payload", {}).get("manifest")
                if not isinstance(manifest, Mapping) or manifest.get("artefact_type") != "spec_02_return":
                    continue
                relative = manifest.get("relative_path")
                content_sha256 = manifest.get("content_sha256")
                if not isinstance(relative, str) or not isinstance(content_sha256, str):
                    raise IntegrityError("SPEC-02 PASS return evidence binding is invalid")
                try:
                    raw = read_contained_regular_file(control_root, relative, label="SPEC-02 return artefact")
                    document = json.loads(raw)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise IntegrityError("SPEC-02 PASS return evidence is unavailable") from exc
                if (
                    not isinstance(document, Mapping)
                    or raw != canonical_bytes(document)
                    or sha256_hex(raw) != content_sha256
                ):
                    raise IntegrityError("SPEC-02 PASS return evidence binding is invalid")
                try:
                    schemas.validate("ars://portfolio/spec-operator-return", document, schema_version="1.0.0")
                except SchemaError as exc:
                    raise IntegrityError("SPEC-02 PASS return evidence binding is invalid") from exc
                returns.append(document)
            if len(returns) != 1 or not _spec_02_pass_rerun_matches(returns[0], payload):
                raise IntegrityError("SPEC-02 PASS lacks bound deterministic rerun evidence")

    return validate_spec_authority


def _runtime_git(
    repository_root: Path,
    *arguments: str,
    text: bool = True,
    unavailable_message: str,
) -> str | bytes:
    """Run one isolated Git observation and preserve runtime error semantics."""

    try:
        result = run_git(
            repository_root,
            *arguments,
            text=text,
            timeout=_GIT_TIMEOUT_SECONDS,
            unavailable_message=unavailable_message,
        )
    except ConfigurationError as exc:
        raise IntegrityError(unavailable_message) from exc
    if result.returncode != 0:
        raise IntegrityError(unavailable_message)
    return result.stdout


def _decision_resolution_authority_matches(command: Command, payload: Mapping[str, Any]) -> bool:
    """Bind nested W2 decision authority to the governed command envelope."""

    return bool(
        payload.get("deciding_actor_id") == command.actor_id
        and payload.get("decision_authority_grant_id") == command.envelope.get("authority_grant_id")
    )


class DiscoveryLedgerReplayError(IntegrityError):
    """A persisted Discovery ledger cannot be reconstructed before command preparation."""


_DISCOVERY_COMMAND_TYPES = DISCOVERY_COMMAND_TYPES


class DiscoveryRuntime:
    """Public, provider-free W11 genesis and Discovery lifecycle seam."""

    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        schemas: SchemaRegistry,
        *,
        catalogue_path: Path,
        authority_resolver: LedgerAuthorityGrantResolver,
        clock: Callable[[], datetime],
        repository_root: Path,
        root_tokens: Mapping[str, Path],
        operational_ledger: EventLedger,
    ) -> None:
        """Bind the governed runtime to exact repository and root configuration.

        Args:
            control_root: Discovery receipt and writer-lock root.
            ledger: Durable Discovery event ledger.
            schemas: Active schema registry used for command and event identities.
            catalogue_path: Exact accepted W11 catalogue path.
            authority_resolver: Canonical current-grant resolver.
            clock: Trusted timezone-aware runtime clock.
            repository_root: Repository root containing the accepted catalogue and authority files.
            root_tokens: Accepted dossier path tokens and their configured physical roots.
            operational_ledger: Canonical same-project Attempt and Lease ledger.

        Raises:
            IntegrityError: If configured paths, project identity, or runtime bindings are inconsistent.
            TypeError: If a canonical authority resolver or concrete operational ledger is not supplied.
        """
        self.control_root = control_root
        self.ledger = ledger
        self.schemas = schemas
        self.catalogue_path = catalogue_path
        try:
            self.repository_root = repository_root.resolve(strict=True)
        except OSError as exc:
            raise IntegrityError("configured repository root is unavailable") from exc
        try:
            resolved_catalogue = catalogue_path.resolve(strict=True)
        except OSError as exc:
            raise IntegrityError("catalogue path is unavailable") from exc
        try:
            resolved_catalogue.relative_to(self.repository_root)
        except ValueError as exc:
            raise IntegrityError("catalogue path is outside configured repository root") from exc
        self.root_tokens = {key: Path(value) for key, value in root_tokens.items()}
        if type(operational_ledger) is not EventLedger:
            raise TypeError("DiscoveryRuntime requires a concrete operational EventLedger")
        if operational_ledger.project_id != ledger.project_id:
            raise IntegrityError("operational ledger project mismatch")
        if operational_ledger is not ledger:
            raise IntegrityError("Discovery and operational state require one atomic ledger")
        self.operational_ledger = operational_ledger
        self.receipts = ReceiptStore(control_root)
        if not isinstance(authority_resolver, LedgerAuthorityGrantResolver):
            raise TypeError("DiscoveryRuntime requires LedgerAuthorityGrantResolver")
        self.authority_resolver = authority_resolver
        self.clock = clock

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        """Authorize and atomically submit one public Discovery command.

        Args:
            envelope: Complete governed command envelope.

        Returns:
            Durable accepted, rejected, or conflict receipt for the exact command.

        Raises:
            ConflictError: If a committed receipt or writer state conflicts with the command identity.
            IntegrityError: If authority, payload, replay state, or the requested transition is invalid.
        """
        command = self._validated_command(envelope)
        remote_proof = self._assay_successor_remote_proof(command)
        with SpecPreparationFence(self.control_root):
            with CompositeWriterLock(
                (self.control_root, self.authority_resolver.control_root, self.operational_ledger.control_root),
                {"command_id": command.command_id},
                lock_factory=WriterLock,
            ):
                authority_evidence = self._resolve_authority(command)
                return self._submit_authorized(command, authority_evidence, assay_successor_remote_proof=remote_proof)

    def prevalidate(
        self,
        envelope: dict[str, Any],
        *,
        prospective_document: Mapping[str, Any] | None = None,
    ) -> None:
        """Prove one command is currently admissible without publishing it."""

        command = self._validated_command(envelope)
        remote_proof = self._assay_successor_remote_proof(command)
        with CompositeWriterLock(
            (self.control_root, self.authority_resolver.control_root, self.operational_ledger.control_root),
            {"command_id": command.command_id, "operation": "prevalidate"},
            lock_factory=WriterLock,
        ):
            self._resolve_authority(command)
            snapshot = self.ledger.snapshot()
            projection = self.replay(snapshot.events)
            scope = (
                command.actor_id,
                command.envelope["authority_grant_id"],
                command.envelope["command_type"],
                command.idempotency_key,
            )
            scoped = [
                event
                for event in snapshot.events
                if (
                    event.get("actor_id"),
                    event.get("authority_grant_id"),
                    event.get("command_type"),
                    event.get("idempotency_key"),
                )
                == scope
            ]
            if scoped:
                first = scoped[0]
                if (
                    first.get("command_id") == command.command_id
                    and first.get("command_payload_hash") == command.payload_hash
                    and first.get("stream_id") == command.target_stream_id
                ):
                    return
                raise ConflictError("idempotency key conflicts with committed Discovery command")
            if any(event.get("command_id") == command.command_id for event in snapshot.events):
                raise ConflictError("command ID conflicts with committed Discovery command")
            observed = snapshot.stream_versions.get(command.target_stream_id, 0)
            if observed != command.expected_stream_version:
                raise ConflictError("Discovery command stream version conflicts")
            self._prepare_transaction(
                command,
                projection,
                events=snapshot.events,
                prospective_document=prospective_document,
                assay_successor_remote_proof=remote_proof,
            )

    def replay(self, events: tuple[dict[str, Any], ...] | None = None) -> dict[str, Any]:
        """Replay one exact ledger snapshot with external SPEC evidence revalidated."""

        ordered = self.ledger.snapshot().events if events is None else events
        validate_spec_authority = self.spec_execution_authority_validator(ordered)

        return replay_discovery(
            ordered,
            schemas=self.schemas,
            authority_state_validator=self.authority_resolver.validate_replayed_administration_state,
            spec_execution_authority_validator=validate_spec_authority,
        )

    def spec_execution_authority_validator(
        self, events: tuple[dict[str, Any], ...]
    ) -> Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], bool], None]:
        """Bind shared replay to exact registered SPEC approval bytes."""

        return build_spec_execution_authority_validator(
            control_root=self.control_root,
            schemas=self.schemas,
            authority_resolver=self.authority_resolver,
            events=events,
            clock=self.clock,
        )

    def _validated_command(self, envelope: dict[str, Any]) -> Command:
        if set(envelope) != _COMMAND_FIELDS or not isinstance(envelope.get("payload"), dict):
            raise IntegrityError("invalid Discovery command envelope")
        command_type = envelope.get("command_type")
        binding = self.schemas.command_binding(str(command_type))
        if binding is None:
            raise IntegrityError(f"inactive Discovery command binding: {command_type}")
        try:
            command = Command(deepcopy(envelope))
            command.payload_hash
        except (TypeError, ValueError) as exc:
            raise IntegrityError("Discovery command canonical payload is invalid") from exc
        if command_type == "ImportAcceptedW11CatalogueGenesis" and command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        return command

    def _assay_successor_remote_proof(self, command: Command) -> SourceCorrectionRemoteProof | None:
        """Resolve a new OR-109 remote proof before either Discovery writer lock."""

        payload = command.envelope["payload"]
        trigger = payload.get("source_correction_trigger")
        if (
            command.envelope["command_type"] != "RecordAssayBarStaleness"
            or payload.get("row_id") != "OR-109"
            or trigger is None
        ):
            return None
        snapshot = self.ledger.snapshot()
        scope = (
            command.actor_id,
            command.envelope["authority_grant_id"],
            command.envelope["command_type"],
            command.idempotency_key,
        )
        if any(
            event.get("command_id") == command.command_id
            or (
                event.get("actor_id"),
                event.get("authority_grant_id"),
                event.get("command_type"),
                event.get("idempotency_key"),
            )
            == scope
            for event in snapshot.events
        ):
            # Exact retries and conflicts are resolved from immutable ledger
            # identity under the writer lock; they must not depend on a later
            # remote tag lookup.
            return None
        document = trigger.get("document") if isinstance(trigger, Mapping) else None
        if not isinstance(document, Mapping):
            raise IntegrityError("invalid Assay-bar staleness transition")
        try:
            return prevalidate_assay_authority_successor_remote(document, schemas=self.schemas)
        except (ConfigurationError, OSError, SchemaError, TypeError, ValueError) as exc:
            raise IntegrityError("invalid Assay-bar staleness transition") from exc

    def _prepare_transaction(
        self,
        command: Command,
        projection: dict[str, Any],
        *,
        events: tuple[dict[str, Any], ...],
        prospective_document: Mapping[str, Any] | None = None,
        assay_successor_remote_proof: SourceCorrectionRemoteProof | None = None,
    ) -> tuple[str, list[tuple[str, str, dict[str, Any]]]]:
        """Prepare and validate one Discovery transaction without publishing it."""

        self._require_admissible_target(command, projection)
        self._require_candidate_target(command, projection)
        row_id, route = _discovery_route(command)
        if route.family == "genesis":
            event_type, event_payload = self._prepare_genesis(command, projection)
            prepared = [(event_type, command.target_stream_id, event_payload)]
        elif route.family == "scout":
            prepared = self._prepare_scout_observation(command, projection)
        elif route.family == "candidate":
            event_type, event_payload = self._prepare_candidate(command, projection)
            prepared = [(event_type, command.target_stream_id, event_payload)]
        elif route.family == "supersede":
            prepared = self._prepare_candidate_supersession(command, projection)
        elif route.family == "assay":
            prepared = self._prepare_assay(command, projection)
        elif route.family == "spike":
            prepared = self._prepare_spike(
                command,
                projection,
                events=events,
                prospective_document=prospective_document,
            )
        elif route.family == "dossier":
            try:
                prepared = self._prepare_dossier(command, projection)
            except DossierAdmissionRejected:
                raise
            except (TypeError, ValueError) as exc:
                raise DossierAdmissionRejected("invalid_canonical_value") from exc
        elif route.family == "assay_authority":
            prepared = self._prepare_assay_bar_authority(
                command,
                projection,
                assay_successor_remote_proof=assay_successor_remote_proof,
            )
        elif route.family == "authority":
            prepared = self._prepare_authority(command, projection)
        else:
            raise IntegrityError(f"unsupported Discovery route family: {route.family}")
        validate_prepared_transaction_contract(row_id, command.payload_hash, prepared)
        return row_id, prepared

    def _resolve_authority(self, command: Command) -> Any:
        """Resolve current canonical scoped authority for one command."""
        command_type = command.envelope["command_type"]
        binding = self.schemas.command_binding(command_type)
        if binding is None:
            raise IntegrityError(f"inactive Discovery command binding: {command_type}")
        identity = self.schemas.resolve_identity(binding.schema_id, binding.schema_version)
        subject_kind = {
            "ImportAcceptedW11CatalogueGenesis": "scope_definition",
            "IngestScoutObservationBatch": "scope_definition",
            "RegisterCandidate": "scope_definition",
            "SupersedeDiscoveryRecord": "scope_definition",
            "RequestAssay": "scope_definition",
            "RecordAssayScore": "scope_definition",
            "RecordAssayPartial": "scope_definition",
            "CancelDiscoveryEvaluation": "scope_definition",
            "ProposeRevisitDecision": "scope_definition",
            "RequestDiscoveryOutcomeReview": "scope_definition",
            "ReviewDiscoveryOutcome": "review",
            "ProposePromotionDecision": "scope_definition",
            "RegisterSpikePlan": "scope_definition",
            "ProposeSpikeExecutionDecision": "scope_definition",
            "StartSpike": "scope_definition",
            "RecordSpikeVerdict": "scope_definition",
            "RegisterAssayRubricContent": "scope_definition",
            "RegisterAssayEvidenceScopeContent": "scope_definition",
            "RecordAssayBarStaleness": "decision",
            "RegisterDossierExpectedSetContent": "scope_definition",
            "RegisterPathRegistrationContent": "scope_definition",
            "ObserveW11AuthorityFile": "scope_definition",
            "RequestW11AuthorityReview": "review",
            "RecordW11AuthorityReview": "review",
            "ProposeW11AuthorityDecision": "decision",
            "ResolveDecision": "decision",
            "AdmitResearchDossier": "scope_definition",
        }.get(command_type)
        if subject_kind is None:
            raise IntegrityError(f"unsupported Discovery authority command: {command_type}")
        subject_id = command.target_stream_id
        if command_type in {
            "RequestAssay",
            "RecordAssayScore",
            "RecordAssayPartial",
            "CancelDiscoveryEvaluation",
            "ProposeRevisitDecision",
            "RequestDiscoveryOutcomeReview",
            "ProposePromotionDecision",
            "RegisterSpikePlan",
            "ProposeSpikeExecutionDecision",
            "StartSpike",
            "RecordSpikeVerdict",
        }:
            subject_id = command.envelope["payload"].get("candidate_id")
            if not isinstance(subject_id, str):
                raise IntegrityError("Discovery lifecycle authority requires candidate_id")
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery authority clock must return an aware datetime")
        return self.authority_resolver.resolve_lifecycle_command(
            command.envelope["authority_grant_id"],
            command.actor_id,
            GrantedCommandIdentity(
                command_type=command_type,
                schema_id=identity.schema_id,
                schema_version=identity.schema_version,
                schema_sha256=identity.sha256,
            ),
            "R2",
            self.ledger.project_id,
            subject_kind,
            subject_id,
            now.astimezone(UTC),
        )

    @staticmethod
    def _require_candidate_target(command: Command, projection: Mapping[str, Any]) -> None:
        """Fence Candidate-scoped authority to the exact lifecycle stream it may mutate."""

        command_type = command.envelope["command_type"]
        if command_type not in {
            "RequestAssay",
            "RecordAssayScore",
            "RecordAssayPartial",
            "CancelDiscoveryEvaluation",
            "ProposeRevisitDecision",
            "RequestDiscoveryOutcomeReview",
            "ProposePromotionDecision",
            "RegisterSpikePlan",
            "ProposeSpikeExecutionDecision",
            "StartSpike",
            "RecordSpikeVerdict",
        }:
            return
        payload = command.envelope["payload"]
        candidate_id = payload.get("candidate_id")
        target_id = command.target_stream_id
        if not isinstance(candidate_id, str) or candidate_id not in projection["candidates"]:
            raise IntegrityError("Discovery lifecycle target is outside authorized Candidate")
        if command_type == "RequestAssay":
            valid = target_id == payload.get("assay_id") and not _discovery_identity_exists(projection, target_id)
        elif command_type == "RequestDiscoveryOutcomeReview":
            valid = target_id == payload.get("review_id") and not _discovery_identity_exists(projection, target_id)
        elif command_type in {
            "ProposeRevisitDecision",
            "ProposePromotionDecision",
            "ProposeSpikeExecutionDecision",
        }:
            valid = target_id == payload.get("decision_id") and not _discovery_identity_exists(projection, target_id)
        elif command_type in {"RecordAssayScore", "RecordAssayPartial"}:
            assay = projection["assays"].get(target_id)
            valid = isinstance(assay, Mapping) and assay.get("candidate_id") == candidate_id
        elif command_type == "RegisterSpikePlan":
            valid = target_id == payload.get("spike_id") and not _discovery_identity_exists(projection, target_id)
        elif command_type in {"StartSpike", "RecordSpikeVerdict"}:
            spike = projection["spikes"].get(target_id)
            valid = isinstance(spike, Mapping) and spike.get("candidate_id") == candidate_id
        elif payload.get("evaluation_kind") == "assay":
            assay = projection["assays"].get(target_id)
            valid = (
                target_id == payload.get("assay_id")
                and isinstance(assay, Mapping)
                and assay.get("candidate_id") == candidate_id
            )
        else:
            spike = projection["spikes"].get(target_id)
            valid = (
                target_id == payload.get("spike_id")
                and isinstance(spike, Mapping)
                and spike.get("candidate_id") == candidate_id
            )
        if not valid:
            raise IntegrityError("Discovery lifecycle target is outside authorized Candidate")

    @staticmethod
    def _require_admissible_target(command: Command, projection: Mapping[str, Any]) -> None:
        """Apply the row registry's global mint-or-advance identity contract."""

        row_id, _ = _discovery_route(command)
        target = command.target_stream_id
        if row_id in _DISCOVERY_MINT_ROWS:
            if row_id == "OR-140":
                foreign_claim = any(
                    target in projection.get(collection, {}) for collection in _DISCOVERY_IDENTITY_COLLECTIONS
                )
                if target != _CATALOGUE_STREAM_ID or projection.get("catalogue") is not None or foreign_claim:
                    raise IntegrityError("Discovery command target identity collision")
                return
            if row_id in {"OR-101", "OR-102"} and projection["authority_streams"].get(target) == "assay_bar":
                return
            if _discovery_identity_exists(projection, target):
                raise IntegrityError("Discovery command target identity collision")
            return
        collection = _DISCOVERY_EXISTING_TARGETS[row_id]
        if collection == "authority_streams":
            authority_kind = command.envelope["payload"].get("authority_kind")
            if projection[collection].get(target) != authority_kind:
                raise IntegrityError("W11 authority stream identity collision")
            return
        if target not in projection.get(collection, {}):
            raise IntegrityError("Discovery command target is owned by another aggregate")

    def _submit_authorized(
        self,
        command: Command,
        authority_evidence: Any,
        *,
        assay_successor_remote_proof: SourceCorrectionRemoteProof | None = None,
    ) -> Receipt:
        """Prepare, append, and receipt one already-authorized command."""
        envelope = command.envelope
        authority_sha256 = authority_evidence.command_resolution.authority_grant_sha256
        idempotency_scope = (
            command.actor_id,
            command.envelope["authority_grant_id"],
            command.envelope["command_type"],
            command.idempotency_key,
        )

        def immutable_envelope_sha256(command_id: str) -> str:
            """Hash the complete envelope persisted for one command identity."""

            return sha256_hex(
                canonical_bytes(
                    {
                        "command_id": command_id,
                        "command_type": envelope["command_type"],
                        "actor_id": command.actor_id,
                        "authority_grant_id": envelope["authority_grant_id"],
                        "authority_grant_sha256": authority_sha256,
                        "idempotency_key": command.idempotency_key,
                        "target_stream_id": command.target_stream_id,
                        "expected_stream_version": command.expected_stream_version,
                        "payload_hash": command.payload_hash,
                    }
                )
            )

        envelope_sha256 = immutable_envelope_sha256(command.command_id)

        def committed_envelope_matches(event: Mapping[str, Any], command_id: str) -> bool:
            """Bind a recovered command id to the complete immutable submission envelope."""

            return bool(
                event.get("command_id") == command_id
                and event.get("command_payload_hash") == command.payload_hash
                and event.get("command_type") == envelope["command_type"]
                and event.get("actor_id") == command.actor_id
                and event.get("authority_grant_id") == envelope["authority_grant_id"]
                and event.get("idempotency_key") == command.idempotency_key
                and event.get("correlation_id") == immutable_envelope_sha256(command_id)
            )

        def committed_transaction(command_id: str) -> tuple[Mapping[str, Any] | None, tuple[dict[str, Any], ...]]:
            """Resolve one command's exact validated contiguous transaction."""

            committed_event = next(
                (event for event in snapshot.events if event.get("command_id") == command_id),
                None,
            )
            if not isinstance(committed_event, Mapping):
                return None, ()
            members = tuple(
                event
                for event in snapshot.events
                if event.get("transaction_id") == committed_event.get("transaction_id")
            )
            if (
                not members
                or any(event.get("command_id") != command_id for event in members)
                or not committed_envelope_matches(committed_event, command_id)
            ):
                raise ConflictError("committed command envelope mismatch")
            return committed_event, members

        def accepted_receipt_matches_transaction(
            receipt: Receipt,
            committed_event: Mapping[str, Any] | None,
            transaction_events: tuple[dict[str, Any], ...],
        ) -> bool:
            """Bind an accepted receipt to its exact committed target mutation."""

            if not isinstance(committed_event, Mapping):
                return False
            target_versions = [
                event["stream_version"]
                for event in transaction_events
                if event.get("stream_id") == command.target_stream_id
            ]
            committed_command_id = committed_event.get("command_id")
            committed_payload_hash = committed_event.get("command_payload_hash")
            transaction_id = committed_event.get("transaction_id")
            if (
                not isinstance(committed_command_id, str)
                or not isinstance(committed_payload_hash, str)
                or not isinstance(transaction_id, str)
                or not target_versions
            ):
                return False
            expected = Receipt(
                status="accepted",
                command_id=committed_command_id,
                payload_hash=committed_payload_hash,
                event_batch_id=transaction_id,
                observed_stream_version=max(target_versions),
                reason_code=None,
            )
            return receipt == expected

        def persist(receipt: Receipt) -> Receipt:
            return self.receipts.write_scoped(
                idempotency_scope,
                authority_sha256,
                command.expected_stream_version,
                receipt,
                project_id=self.ledger.project_id,
                target_stream_id=command.target_stream_id,
            )

        snapshot = self.ledger.snapshot()
        try:
            projection = self.replay(snapshot.events)
        except (IntegrityError, TypeError, ValueError) as exc:
            raise DiscoveryLedgerReplayError(
                "persisted Discovery ledger failed replay before command preparation"
            ) from exc
        scoped = self.receipts.load_scoped(
            idempotency_scope,
            command.payload_hash,
            authority_sha256,
            command.expected_stream_version,
            project_id=self.ledger.project_id,
            target_stream_id=command.target_stream_id,
        )
        if scoped is not None:
            scoped_committed, scoped_transaction = committed_transaction(scoped.command_id)
            if scoped.status == "accepted" and (
                not accepted_receipt_matches_transaction(scoped, scoped_committed, scoped_transaction)
            ):
                raise ConflictError("idempotency receipt committed transaction mismatch")
            if scoped.status != "accepted" and scoped_committed is not None:
                raise ConflictError("idempotency receipt committed transaction mismatch")
            primary = self.receipts.load(scoped.command_id)
            if primary is not None and primary != scoped:
                raise ConflictError("idempotency primary receipt mismatch")
            if primary is None:
                self.receipts.write(scoped)
            return scoped
        committed, transaction_events = committed_transaction(command.command_id)
        existing = self.receipts.load(command.command_id)
        if existing is not None:
            if (
                existing.status != "accepted"
                or existing.payload_hash != command.payload_hash
                or not isinstance(committed, Mapping)
                or not committed_envelope_matches(committed, command.command_id)
                or not accepted_receipt_matches_transaction(existing, committed, transaction_events)
            ):
                raise ConflictError("command receipt committed transaction mismatch")
            return persist(existing)
        if committed is not None:
            target_versions = [
                event["stream_version"]
                for event in transaction_events
                if event.get("stream_id") == command.target_stream_id
            ]
            if not target_versions:
                raise ConflictError("committed command target transaction mismatch")
            receipt = Receipt(
                status="accepted",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=committed["transaction_id"],
                observed_stream_version=max(target_versions),
                reason_code=None,
            )
            return persist(receipt)
        observed = snapshot.stream_versions.get(command.target_stream_id, 0)
        if observed != command.expected_stream_version:
            receipt = Receipt(
                status="conflict",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=None,
                observed_stream_version=observed,
                reason_code="stream_version_conflict",
            )
            return persist(receipt)

        row_id, prepared = self._prepare_transaction(
            command,
            projection,
            events=snapshot.events,
            assay_successor_remote_proof=assay_successor_remote_proof,
        )
        command_binding = self.schemas.command_binding(envelope["command_type"])
        if command_binding is None:
            raise IntegrityError(f"inactive Discovery command binding: {envelope['command_type']}")
        binding = self.schemas.resolve_identity(command_binding.schema_id, command_binding.schema_version)
        occurred_at = self.clock()
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise IntegrityError("Discovery runtime clock must return an aware datetime")
        occurred_at_value = occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z")

        def event_schema(event_type: str, payload: Mapping[str, Any]) -> tuple[str, str]:
            """Resolve an exact producer binding, falling back only for Discovery shadow events."""

            shadow_keys = {
                "owner_row_id",
                "authority_kind",
                "authority_event_type",
                "authority_payload",
            }
            is_authority_shadow = (
                set(payload) == shadow_keys
                and payload.get("authority_event_type") == event_type
                and isinstance(payload.get("authority_payload"), Mapping)
            )
            if is_authority_shadow:
                return "ars://core/event", "1.0.0"
            if "authority_event_type" in payload:
                raise IntegrityError("invalid Discovery authority shadow payload")
            event_binding = self.schemas.event_binding(event_type, envelope["command_type"])
            if event_binding is not None:
                return event_binding.schema_id, event_binding.schema_version
            if self.schemas.has_producer_bindings(event_type):
                raise IntegrityError(
                    f"inactive Discovery event producer binding: {event_type}/{envelope['command_type']}"
                )
            return "ars://core/event", "1.0.0"

        event_records = []
        for prepared_event_type, prepared_stream_id, prepared_payload in prepared:
            persisted_payload = deepcopy(prepared_payload)
            if prepared_event_type == "LeaseReleased" and envelope["command_type"] in {
                "RecordSpikeVerdict",
                "CancelDiscoveryEvaluation",
            }:
                persisted_payload["observed_at"] = occurred_at_value
            schema_id, schema_version = event_schema(prepared_event_type, persisted_payload)
            event_records.append(
                {
                    "event_type": prepared_event_type,
                    "schema_id": schema_id,
                    "schema_version": schema_version,
                    "stream_id": prepared_stream_id,
                    "command_id": command.command_id,
                    "command_type": envelope["command_type"],
                    "command_schema_id": binding.schema_id,
                    "command_schema_version": binding.schema_version,
                    "command_schema_sha256": binding.raw_bytes_sha256,
                    "idempotency_key": command.idempotency_key,
                    "command_payload_hash": command.payload_hash,
                    "correlation_id": envelope_sha256,
                    "causation_id": None,
                    "actor_id": command.actor_id,
                    "authority_grant_id": envelope["authority_grant_id"],
                    "occurred_at": occurred_at_value,
                    "payload": persisted_payload,
                }
            )
        result = self.ledger.append(event_records, snapshot=snapshot)
        receipt = Receipt(
            status="accepted",
            command_id=command.command_id,
            payload_hash=command.payload_hash,
            event_batch_id=result["event_batch_id"],
            observed_stream_version=result["resulting_stream_versions"][command.target_stream_id],
            reason_code=None,
        )
        return persist(receipt)

    def _prepare_authority(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare one ordered W11 authority transition."""
        if projection.get("catalogue") is None:
            raise IntegrityError("W11 genesis is required before generic W11 authority")
        payload = command.envelope["payload"]
        row = payload.get("row_id")
        routes = {
            "OR-110": ("dossier_expected_set", "register"),
            "OR-111": ("dossier_expected_set", "observe"),
            "OR-112": ("dossier_expected_set", "request_review"),
            "OR-113": ("dossier_expected_set", "record_review"),
            "OR-114": ("dossier_expected_set", "propose"),
            "OR-115": ("dossier_expected_set", "resolve"),
            "OR-116": ("path_registration", "register"),
            "OR-117": ("path_registration", "observe"),
            "OR-118": ("path_registration", "request_review"),
            "OR-119": ("path_registration", "record_review"),
            "OR-120": ("path_registration", "propose"),
            "OR-121": ("path_registration", "resolve"),
        }
        if row not in routes:
            raise IntegrityError("invalid W11 authority row")
        kind, action = routes[row]
        if payload.get("authority_kind") != kind:
            raise IntegrityError("W11 authority kind mismatch")
        if action in {"register", "request_review", "propose"} and _discovery_identity_exists(
            projection, command.target_stream_id
        ):
            raise IntegrityError("W11 authority stream identity collision")
        current_authority = projection["authorities"].get(kind, {})
        if action == "record_review" and command.target_stream_id != current_authority.get("review_id"):
            raise IntegrityError("W11 authority review stream mismatch")
        if action == "propose" and command.target_stream_id != payload.get("decision_id"):
            raise IntegrityError("W11 authority decision stream mismatch")
        if action == "resolve" and command.target_stream_id != payload.get("decision_id"):
            raise IntegrityError("W11 authority decision stream mismatch")
        transition_payload = {
            key: deepcopy(value) for key, value in payload.items() if key not in {"row_id", "authority_kind"}
        }
        if action == "observe":
            current = projection["authorities"].get(kind)
            if not isinstance(current, dict) or command.target_stream_id != projection["authority_subject_streams"].get(
                kind
            ):
                raise IntegrityError("authority subject is not registered")
            subject = current.get("subject")
            if not isinstance(subject, dict):
                raise IntegrityError("authority subject is invalid")
            repository_path = subject.get("authority_file_path")
            if not isinstance(repository_path, str) or not repository_path:
                raise IntegrityError("authority file path is not sealed")
            repository_root = self.repository_root
            lexical_path = Path(repository_path)
            if lexical_path.is_absolute() or lexical_path.as_posix() != repository_path:
                raise IntegrityError("authority file path is not canonical")
            authority_file = (repository_root / repository_path).resolve(strict=True)
            try:
                authority_file.relative_to(repository_root)
            except ValueError as exc:
                raise IntegrityError("authority file escapes repository root") from exc
            raw = authority_file.read_bytes()
            file_sha256 = sha256_hex(raw)
            relative_path = authority_file.relative_to(repository_root).as_posix()
            if relative_path != repository_path:
                raise IntegrityError("authority file path alias is forbidden")
            git_commit = str(
                _runtime_git(
                    repository_root,
                    "rev-parse",
                    "HEAD",
                    unavailable_message="authority file lacks current Git identity",
                )
            ).strip()
            git_blob = str(
                _runtime_git(
                    repository_root,
                    "rev-parse",
                    f"{git_commit}:{relative_path}",
                    unavailable_message="authority file lacks current Git identity",
                )
            ).strip()
            committed_raw = _runtime_git(
                repository_root,
                "show",
                f"{git_commit}:{relative_path}",
                text=False,
                unavailable_message="authority file lacks current Git identity",
            )
            computed_blob = _git_blob(raw)
            if committed_raw != raw or computed_blob != git_blob:
                raise IntegrityError("authority file differs from captured Git bytes")
            try:
                serialized_subject = json.loads(committed_raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntegrityError("authority file is not canonical JSON content") from exc
            semantic_subject = {
                key: value
                for key, value in subject.items()
                if key != "subject_sha256" and not key.startswith("authority_file_")
            }
            if serialized_subject != semantic_subject:
                raise IntegrityError("authority file content does not match registered subject")
            if (
                subject.get("authority_file_size") != len(raw)
                or subject.get("authority_file_sha256") != file_sha256
                or subject.get("authority_file_git_commit") != git_commit
                or subject.get("authority_file_git_blob") != git_blob
            ):
                raise IntegrityError("authority file identity mismatch")
            transition_payload = {
                "subject_sha256": current["subject_sha256"],
                "repository_path": relative_path,
                "git_commit": git_commit,
                "git_blob": git_blob,
                "file_size": len(raw),
                "file_sha256": file_sha256,
            }
            if kind == "path_registration" and is_portable_path_subject(subject):
                transition_payload["portable_physical_binding"] = self._observe_portable_spec_root(subject, git_commit)
        elif action == "resolve":
            # The ledger replaces this preparation-only marker with its atomic
            # transaction identity in both persisted authority shadows.
            transition_payload["transaction_id"] = "pending-ledger-transaction"
        try:
            events = prepare_authority_transition(
                events=projection["authority_events"],
                kind=kind,
                action=action,
                actor_id=command.actor_id,
                payload=transition_payload,
            )
        except ValueError as exc:
            raise IntegrityError(str(exc)) from exc
        current = projection["authorities"].get(kind, {})
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery authority clock must return an aware datetime")
        normalized_now = now.astimezone(UTC)

        def stable_id(prefix: str, suffix: int) -> str:
            return (
                f"{prefix}_019fed25-b33e-7740-b280-{(1100 if kind == 'dossier_expected_set' else 1200) + suffix:012d}"
            )

        def persisted_payload(event: dict[str, object]) -> dict[str, Any]:
            event_type = str(event["event_type"])
            shadow = event["payload"]
            current_time = normalized_now.isoformat().replace("+00:00", "Z")
            deadline = (normalized_now + timedelta(days=1)).isoformat().replace("+00:00", "Z")
            if event_type == "ReviewRequested":
                return {
                    "review_type": "provenance",
                    "new_review_id": command.target_stream_id,
                    "subject_ids": [stable_id("obj", 3)],
                    "subject_hashes": [current["subject_sha256"]],
                    "governing_refs": [f"W11:{event['owner_row_id']}", f"authority-kind:{kind}"],
                    "review_questions": [
                        "Does the exact authority subject and independently observed file identity match?"
                    ],
                    "required_evidence_refs": [current["file_sha256"]],
                    "required_lanes": ["provenance"],
                    "reviewer_capability": [shadow["reviewer_actor_id"]],
                    "required_independence_grade": "independent",
                    "visibility_policy": "owner-visible",
                    "allowed_verdicts": ["approve", "changes_requested", "reject", "unable_to_verify"],
                    "satisfaction_authority": "ars://portfolio/policy/w11-authority-review@1.0.0",
                    "deadline": deadline,
                    "escalation_rule": "owner-ruling",
                }
            if event_type == "ReviewVerdictRecorded":
                return {
                    "review_id": current["review_id"],
                    "verdict": shadow["verdict"],
                    "findings": [],
                    "required_evidence_refs": [current["file_sha256"]],
                    "limitations": [],
                    "conditions": [],
                    "reviewer_actor_id": command.actor_id,
                    "reviewer_profile": "independent-w11-authority-reviewer",
                    "reviewer_session": f"session-{kind}",
                    "reviewer_model_metadata": "independent-runtime-review",
                    "context_manifest_id": stable_id("ctx", 1),
                    "context_manifest_sha256": shadow["reconstruction_sha256"],
                    "unchanged_subject_sha256": shadow["unchanged_subject_sha256"],
                    "producing_attempt_id": stable_id("att", 2),
                    "trace_visibility_evidence_refs": [current["file_sha256"]],
                    "computed_independence_grade": "independent",
                }
            if event_type == "DecisionProposed":
                return {
                    "new_decision_id": shadow["decision_id"],
                    "question": f"Accept exact {kind} authority?",
                    "recommendation": shadow["proposed_decision"],
                    "options": ["accept", "reject"],
                    "decision_revision": 1,
                    "decision_kind": "design_lock",
                    "governing_evidence_refs": [current["file_sha256"], f"authority-kind:{kind}"],
                    "affected_task_ids": [],
                    "affected_claim_ids": [],
                    "required_authority": "owner",
                    "expires_at": deadline,
                    "review_date": current_time,
                    "consequences": [f"the exact {kind} subject becomes admission authority"],
                }
            if event_type == "DecisionResolved":
                return {
                    "decision_id": shadow["decision_id"],
                    "selected_option": shadow["decision"],
                    "effective_scope": f"exact {kind} subject",
                    "effective_at": current_time,
                    "decision_revision": 1,
                    "deciding_actor_id": command.actor_id,
                    "decision_authority_grant_id": command.envelope["authority_grant_id"],
                    "governing_evidence_refs": [current["file_sha256"]],
                    "considered_review_ids": [current["review_id"]],
                    "permitted_commands": ["AdmitResearchDossier"],
                    "superseded_decision_ids": [],
                    "conditions": [],
                    "revisit_triggers": ["authority subject changes"],
                }
            persisted_shadow = deepcopy(shadow)
            if isinstance(persisted_shadow, dict):
                persisted_shadow.pop("transaction_id", None)
            return {
                "owner_row_id": event["owner_row_id"],
                "authority_kind": event["authority_kind"],
                "authority_event_type": event["event_type"],
                "authority_payload": persisted_shadow,
            }

        return [
            (
                str(event["event_type"]),
                command.target_stream_id,
                persisted_payload(event),
            )
            for event in events
        ]

    def _observe_portable_spec_root(self, subject: Mapping[str, Any], git_commit: str) -> dict[str, Any]:
        """Verify stable SPEC member bindings and derive this checkout's root identity."""

        try:
            validate_portable_path_subject(subject)
        except ValueError as exc:
            raise IntegrityError(str(exc)) from exc
        configured_root = self.root_tokens.get("repository")
        try:
            if configured_root is None or configured_root.resolve(strict=True) != self.repository_root:
                raise IntegrityError("portable repository token does not resolve to operator repository")
        except OSError as exc:
            raise IntegrityError("portable repository token is unavailable") from exc
        dirty = _runtime_git(
            self.repository_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--ignore-submodules=none",
            unavailable_message="portable repository cleanliness is unavailable",
        )
        if dirty:
            raise IntegrityError("portable repository contains dirty or uncommitted content")
        observations: list[dict[str, Any]] = []
        supplied_member_set = tuple(
            (str(member.get("alias")), str(member.get("relative_path")))
            for member in subject["required_member_bindings"]
            if isinstance(member, Mapping)
        )
        if supplied_member_set != PORTABLE_SPEC_REQUIRED_MEMBERS:
            raise IntegrityError("portable SPEC member set differs from exact route authority")
        for expected in subject["required_member_bindings"]:
            relative_path = expected["relative_path"]
            lexical_path = Path(relative_path)
            if lexical_path.is_absolute() or lexical_path.as_posix() != relative_path:
                raise IntegrityError("portable SPEC member path is not canonical")
            try:
                member_path = (self.repository_root / lexical_path).resolve(strict=True)
                member_path.relative_to(self.repository_root)
                raw = member_path.read_bytes()
                committed = _runtime_git(
                    self.repository_root,
                    "show",
                    f"{git_commit}:{relative_path}",
                    text=False,
                    unavailable_message="portable SPEC member lacks current Git identity",
                )
                git_blob = str(
                    _runtime_git(
                        self.repository_root,
                        "rev-parse",
                        f"{git_commit}:{relative_path}",
                        unavailable_message="portable SPEC member lacks current Git identity",
                    )
                ).strip()
            except (OSError, ValueError) as exc:
                raise IntegrityError("portable SPEC member lacks current Git identity") from exc
            observation = {
                "alias": expected["alias"],
                "relative_path": relative_path,
                "size_bytes": len(raw),
                "sha256": sha256_hex(raw),
                "git_blob": git_blob,
            }
            if raw != committed or observation != dict(expected):
                raise IntegrityError("portable SPEC member binding differs")
            observations.append(observation)
        return {
            "root_id": "repository",
            "root_token": "repository",
            "registration_revision": 1,
            "registration_hash": registered_root_identity_hash(self.repository_root),
            "git_commit": git_commit,
            "members_sha256": sha256_hex(canonical_bytes(observations)),
        }

    def _current_assay_spec_source_hashes(self) -> tuple[str, str]:
        """Hash the current committed route package and SPEC-01 source."""

        resolved: dict[str, str] = {}
        for alias, relative_path in PORTABLE_SPEC_REQUIRED_MEMBERS[:2]:
            raw = read_contained_regular_file(
                self.repository_root,
                relative_path,
                label=f"current {alias} source",
            )
            committed = _runtime_git(
                self.repository_root,
                "show",
                f"HEAD:{relative_path}",
                text=False,
                unavailable_message=f"current {alias} source lacks Git identity",
            )
            if raw != committed:
                raise IntegrityError(f"current {alias} source differs from committed bytes")
            resolved[alias] = sha256_hex(raw)
        return resolved["route-package"], resolved["SPEC-01"]

    def _prepare_assay_bar_authority(
        self,
        command: Command,
        projection: dict[str, Any],
        *,
        assay_successor_remote_proof: SourceCorrectionRemoteProof | None = None,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare the exact OR-101--OR-109 Assay-bar authority transition."""

        if projection.get("catalogue") is None:
            raise IntegrityError("W11 genesis is required before Assay-bar authority")
        payload = command.envelope["payload"]
        row = payload.get("row_id")
        state = projection["assay_bar_authority"]
        if payload.get("authority_kind") != "assay_bar":
            raise IntegrityError("Assay-bar authority kind mismatch")

        def wrapped(event_type: str, shadow: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]]:
            return (
                event_type,
                command.target_stream_id,
                {
                    "owner_row_id": row,
                    "authority_kind": "assay_bar",
                    "authority_event_type": event_type,
                    "authority_payload": deepcopy(dict(shadow)),
                },
            )

        if row in {"OR-101", "OR-102"}:
            expected_command = "RegisterAssayRubricContent" if row == "OR-101" else "RegisterAssayEvidenceScopeContent"
            kind = "rubric" if row == "OR-101" else "scope"
            event_type = "AssayRubricContentRegistered" if kind == "rubric" else "AssayEvidenceScopeContentRegistered"
            content = payload.get("content")
            path = payload.get("authority_file_path")
            schema_id = (
                "ars://portfolio/assay-rubric-content"
                if kind == "rubric"
                else "ars://portfolio/assay-evidence-scope-content"
            )
            predecessor_contents = state.get("predecessor_contents")
            prior_kind = predecessor_contents.get(kind) if isinstance(predecessor_contents, Mapping) else None
            prior_content = prior_kind.get("content") if isinstance(prior_kind, Mapping) else None
            same_kind_successor = bool(
                isinstance(prior_content, Mapping) and command.target_stream_id == prior_content.get("record_id")
            )
            if (
                command.envelope["command_type"] != expected_command
                or not isinstance(content, dict)
                or not isinstance(path, str)
                or not path
                or command.target_stream_id != content.get("record_id")
                or content.get("created_by_actor_id") != command.actor_id
                or (state.get("status") == "stale" and kind != "rubric")
                or (
                    state.get("status") != "stale"
                    and _discovery_identity_exists(projection, command.target_stream_id)
                    and not same_kind_successor
                )
            ):
                raise IntegrityError("invalid Assay-bar content registration")
            try:
                self.schemas.validate(schema_id, content, schema_version="1.0.0")
            except SchemaError as exc:
                raise IntegrityError("invalid Assay-bar content") from exc
            route_sha256, spec_01_sha256 = self._current_assay_spec_source_hashes()
            if not _assay_content_matches_current_spec_sources(
                content,
                kind=kind,
                route_sha256=route_sha256,
                spec_01_sha256=spec_01_sha256,
            ):
                raise IntegrityError("Assay-bar content does not bind the current SPEC route")
            axis_definitions = content.get("axis_definitions") if kind == "rubric" else ()
            if kind == "rubric" and (
                not isinstance(axis_definitions, list)
                or any(
                    isinstance(definition, Mapping) and definition.get("value_type") == "number"
                    for definition in axis_definitions
                )
            ):
                raise IntegrityError("numeric Assay rubric is not P0-canonical; use an explicit scaled integer")
            try:
                content_digest = assay_content_sha256(content)
            except (TypeError, ValueError) as exc:
                raise IntegrityError("Assay-bar content is not P0-canonical") from exc
            if content_digest != content.get("content_hash"):
                raise IntegrityError("Assay-bar content hash mismatch")
            if kind in state["contents"] and state.get("status") != "stale":
                raise IntegrityError("Assay-bar content identity collision")
            if kind == "scope":
                rubric = state["contents"].get("rubric")
                if not isinstance(rubric, dict) or content.get("rubric_ref") != {
                    "id": rubric["content"]["record_id"],
                    "record_revision": rubric["content"]["record_revision"],
                    "content_hash": rubric["content_sha256"],
                }:
                    raise IntegrityError("Assay scope does not bind the current rubric")
            shadow = {
                "content": deepcopy(content),
                "content_sha256": content["content_hash"],
                "authority_file_path": path,
                "actor_id": command.actor_id,
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": event_type,
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [wrapped(event_type, shadow)]

        if row in {"OR-103", "OR-104"}:
            kind = "rubric" if row == "OR-103" else "scope"
            content_state = state["contents"].get(kind)
            content = content_state.get("content") if isinstance(content_state, Mapping) else None
            if (
                command.envelope["command_type"] != "ObserveW11AuthorityFile"
                or not isinstance(content_state, dict)
                or not isinstance(content, Mapping)
                or command.target_stream_id != content.get("record_id")
            ):
                raise IntegrityError("Assay-bar content is not registered")
            observation = self._observe_assay_authority_content(content_state)
            shadow = {"content_kind": kind, "actor_id": command.actor_id, **observation}
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "W11AuthorityFileObserved",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [wrapped("W11AuthorityFileObserved", shadow)]

        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery authority clock must return an aware datetime")
        current_time = now.astimezone(UTC).isoformat().replace("+00:00", "Z")
        deadline = (now.astimezone(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")

        if row == "OR-105":
            producer_ref = payload.get("prospective_producer_ref")
            reviewer = payload.get("reviewer_actor_id")
            if (
                command.envelope["command_type"] != "RequestW11AuthorityReview"
                or state.get("status") != "observed"
                or not isinstance(producer_ref, dict)
                or not isinstance(reviewer, str)
                or reviewer == producer_ref.get("id")
                or _discovery_identity_exists(projection, command.target_stream_id)
            ):
                raise IntegrityError("invalid Assay-bar review request")
            subject = {
                "rubric_sha256": state["contents"]["rubric"]["content_sha256"],
                "scope_sha256": state["contents"]["scope"]["content_sha256"],
                "rubric_file_sha256": state["observations"]["rubric"]["file_sha256"],
                "scope_file_sha256": state["observations"]["scope"]["file_sha256"],
                "prospective_producer_ref": producer_ref,
            }
            subject_hash = sha256_hex(canonical_bytes(subject))
            shadow = {
                "actor_id": command.actor_id,
                "reviewer_actor_id": reviewer,
                "review_id": command.target_stream_id,
                "subject_sha256": subject_hash,
                "prospective_producer_ref": deepcopy(producer_ref),
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "ReviewRequested",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [
                (
                    "ReviewRequested",
                    command.target_stream_id,
                    {
                        "review_type": "provenance",
                        "new_review_id": command.target_stream_id,
                        "subject_ids": [
                            state["contents"]["rubric"]["content"]["record_id"],
                            state["contents"]["scope"]["content"]["record_id"],
                        ],
                        "subject_hashes": [subject_hash],
                        "governing_refs": [
                            "W11:OR-105",
                            "authority-kind:assay_bar",
                            "prospective-producer:" + json.dumps(producer_ref, sort_keys=True, separators=(",", ":")),
                        ],
                        "review_questions": [
                            "Does the exact Assay bar bind both observed contents and producer relation?"
                        ],
                        "required_evidence_refs": [
                            state["observations"]["rubric"]["file_sha256"],
                            state["observations"]["scope"]["file_sha256"],
                        ],
                        "required_lanes": ["provenance"],
                        "reviewer_capability": [reviewer],
                        "required_independence_grade": "independent",
                        "visibility_policy": "owner-visible",
                        "allowed_verdicts": ["approve", "changes_requested", "reject", "unable_to_verify"],
                        "satisfaction_authority": "ars://portfolio/policy/w11-authority-review@1.0.0",
                        "deadline": deadline,
                        "escalation_rule": "owner-ruling",
                    },
                )
            ]

        if row == "OR-106":
            if (
                command.envelope["command_type"] != "RecordW11AuthorityReview"
                or state.get("status") != "review_requested"
                or command.target_stream_id != state.get("review_id")
            ):
                raise IntegrityError("invalid Assay-bar review verdict")
            shadow = {
                "actor_id": command.actor_id,
                "verdict": payload.get("verdict"),
                "unchanged_subject_sha256": payload.get("unchanged_subject_sha256"),
                "context_manifest_id": "ctx_019fed25-b33e-7740-b280-000000000105",
                "reconstruction_sha256": payload.get("reconstruction_sha256"),
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "ReviewVerdictRecorded",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [
                (
                    "ReviewVerdictRecorded",
                    command.target_stream_id,
                    {
                        "review_id": state["review_id"],
                        "verdict": payload.get("verdict"),
                        "findings": [],
                        "required_evidence_refs": [state["subject_sha256"]],
                        "limitations": [],
                        "conditions": [],
                        "reviewer_actor_id": command.actor_id,
                        "reviewer_profile": "independent-assay-bar-reviewer",
                        "reviewer_session": "session-assay-bar",
                        "reviewer_model_metadata": "independent-runtime-review",
                        "context_manifest_id": "ctx_019fed25-b33e-7740-b280-000000000105",
                        "context_manifest_sha256": payload.get("reconstruction_sha256"),
                        "unchanged_subject_sha256": payload.get("unchanged_subject_sha256"),
                        "producing_attempt_id": "att_019fed25-b33e-7740-b280-000000000106",
                        "trace_visibility_evidence_refs": [state["subject_sha256"]],
                        "computed_independence_grade": "independent",
                    },
                )
            ]

        if row == "OR-107":
            if (
                command.envelope["command_type"] != "ProposeW11AuthorityDecision"
                or state.get("status") != "reviewed"
                or _discovery_identity_exists(projection, command.target_stream_id)
            ):
                raise IntegrityError("invalid Assay-bar decision proposal")
            shadow = {
                "actor_id": command.actor_id,
                "decision_id": command.target_stream_id,
                "proposed_decision": payload.get("proposed_decision"),
                "subject_sha256": state["subject_sha256"],
            }
            try:
                replay_assay_bar_authority(
                    (
                        *projection["assay_bar_authority_events"],
                        {
                            "owner_row_id": row,
                            "authority_kind": "assay_bar",
                            "event_type": "DecisionProposed",
                            "payload": shadow,
                        },
                    )
                )
            except ValueError as exc:
                raise IntegrityError(str(exc)) from exc
            return [
                (
                    "DecisionProposed",
                    command.target_stream_id,
                    {
                        "new_decision_id": command.target_stream_id,
                        "question": "Accept the exact current Assay bar?",
                        "recommendation": payload.get("proposed_decision"),
                        "options": ["accept", "reject"],
                        "decision_revision": 1,
                        "decision_kind": "design_lock",
                        "governing_evidence_refs": [state["subject_sha256"], "authority-kind:assay_bar"],
                        "affected_task_ids": [],
                        "affected_claim_ids": [],
                        "required_authority": "owner",
                        "expires_at": deadline,
                        "review_date": current_time,
                        "consequences": ["the exact Assay bar becomes current collection authority"],
                    },
                )
            ]

        if row == "OR-108":
            if (
                command.envelope["command_type"] != "ResolveDecision"
                or state.get("status") != "decision_proposed"
                or command.target_stream_id != state.get("decision_id")
                or payload.get("decision_id") != state.get("decision_id")
                or payload.get("decision") != "accept"
            ):
                raise IntegrityError("invalid Assay-bar owner resolution")
            resolved = {
                "decision_id": state["decision_id"],
                "selected_option": "accept",
                "effective_scope": "exact current Assay bar",
                "effective_at": current_time,
                "decision_revision": 1,
                "deciding_actor_id": command.actor_id,
                "decision_authority_grant_id": command.envelope["authority_grant_id"],
                "governing_evidence_refs": [state["subject_sha256"]],
                "considered_review_ids": [state["review_id"]],
                "permitted_commands": ["RequestAssay"],
                "superseded_decision_ids": [],
                "conditions": [],
                "revisit_triggers": ["rubric, scope, or producer relation changes"],
            }
            acceptance = {
                "subject_sha256": state["subject_sha256"],
                "rubric_ref": {
                    "id": state["contents"]["rubric"]["content"]["record_id"],
                    "record_revision": state["contents"]["rubric"]["content"]["record_revision"],
                    "content_hash": state["contents"]["rubric"]["content_sha256"],
                },
                "scope_ref": {
                    "id": state["contents"]["scope"]["content"]["record_id"],
                    "record_revision": state["contents"]["scope"]["content"]["record_revision"],
                    "content_hash": state["contents"]["scope"]["content_sha256"],
                },
                "rubric_file_sha256": state["observations"]["rubric"]["file_sha256"],
                "scope_file_sha256": state["observations"]["scope"]["file_sha256"],
                "review_id": state["review_id"],
                "decision_id": state["decision_id"],
                "required_axis_set_hash": state["contents"]["rubric"]["content"]["required_axis_set_hash"],
                "scope_closure_hash": state["contents"]["scope"]["content"]["scope_closure_algorithm_hash"],
                "prospective_producer_ref": deepcopy(state["prospective_producer_ref"]),
                "producer_relation_sha256": state["producer_relation_sha256"],
                "acceptor_actor_id": command.actor_id,
            }
            return [
                ("DecisionResolved", command.target_stream_id, resolved),
                wrapped("AssayBarAccepted", acceptance),
            ]

        if row == "OR-109":
            required_fields = {
                "row_id",
                "authority_kind",
                "acceptance_sha256",
                "trigger_evidence_refs",
            }
            if "source_correction_trigger" in payload:
                required_fields.add("source_correction_trigger")
            proof: dict[str, Any] | None = None
            validation_projection = projection
            source_trigger = payload.get("source_correction_trigger")
            if isinstance(source_trigger, Mapping):
                from research_system.methods.registration import CandidateRegistration

                artefact_ref = source_trigger.get("artefact_ref")
                document = source_trigger.get("document")
                artefact_id = artefact_ref.get("id") if isinstance(artefact_ref, Mapping) else None
                artefact = projection.get("artefact_streams", {}).get(artefact_id)
                manifest = artefact.get("manifest") if isinstance(artefact, Mapping) else None
                registration_actor = artefact.get("registration_actor_id") if isinstance(artefact, Mapping) else None
                if not (
                    isinstance(artefact_id, str)
                    and isinstance(document, Mapping)
                    and isinstance(manifest, dict)
                    and isinstance(registration_actor, str)
                ):
                    raise IntegrityError("invalid Assay-bar staleness transition")
                try:
                    validate_assay_authority_successor_document(
                        document,
                        registration=CandidateRegistration(
                            artefact_id=artefact_id,
                            project_id=str(manifest.get("project_id", "assay-authority-successor")),
                            actor_id=registration_actor,
                            authority_grant_id="validated-by-record-assay-bar-staleness",
                            submitted_at=current_time,
                            correlation_id=command.command_id,
                            reason="Seal the exact validated Assay authority successor.",
                            manifest=manifest,
                        ),
                        repository_root=self.repository_root,
                        schemas=self.schemas,
                        _remote_proof=assay_successor_remote_proof,
                    )
                    successor_hashes = successor_document_hashes(document)
                except (ConfigurationError, OSError, SchemaError, TypeError, ValueError) as exc:
                    raise IntegrityError("invalid Assay-bar staleness transition") from exc
                proof = {
                    "actor_id": command.actor_id,
                    "artefact_ref": deepcopy(dict(artefact_ref)),
                    "document_sha256": artefact_ref.get("content_hash"),
                    "git_commit": document.get("git_commit"),
                    "governed_sources": deepcopy(document.get("governed_sources")),
                    "successor_content_hashes": successor_hashes,
                }
                validation_projection = deepcopy(projection)
                validation_projection.setdefault("assay_authority_successor_proofs", {})[artefact_id] = deepcopy(proof)
            if (
                command.envelope["command_type"] != "RecordAssayBarStaleness"
                or state.get("status") != "accepted"
                or set(payload) != required_fields
                or payload.get("acceptance_sha256") != state.get("acceptance_sha256")
                or not _assay_staleness_matches(payload, validation_projection, schemas=self.schemas)
            ):
                raise IntegrityError("invalid Assay-bar staleness transition")
            staleness = {
                "acceptance_sha256": state["acceptance_sha256"],
                "trigger_evidence_refs": deepcopy(payload["trigger_evidence_refs"]),
                "effective_at": current_time,
                "actor_id": command.actor_id,
            }
            if "source_correction_trigger" in payload:
                staleness["source_correction_trigger"] = deepcopy(payload["source_correction_trigger"])
            prepared = []
            if proof is not None:
                prepared.append(wrapped("AssayAuthoritySuccessorRegistered", proof))
            prepared.append(
                wrapped(
                    "AssayBarStaled",
                    staleness,
                )
            )
            return prepared
        raise IntegrityError("invalid Assay-bar authority row")

    def _observe_assay_authority_content(self, content_state: Mapping[str, Any]) -> dict[str, Any]:
        """Observe one registered Assay authority file at an exact Git commit:path."""

        repository_path = content_state.get("authority_file_path")
        content = content_state.get("content")
        if not isinstance(repository_path, str) or not isinstance(content, dict):
            raise IntegrityError("invalid Assay authority content state")
        lexical_path = Path(repository_path)
        if lexical_path.is_absolute() or lexical_path.as_posix() != repository_path:
            raise IntegrityError("authority file path is not canonical")
        try:
            authority_file = (self.repository_root / repository_path).resolve(strict=True)
            authority_file.relative_to(self.repository_root)
            raw = authority_file.read_bytes()
        except (OSError, ValueError) as exc:
            raise IntegrityError("authority file is unavailable") from exc
        relative_path = authority_file.relative_to(self.repository_root).as_posix()
        if relative_path != repository_path:
            raise IntegrityError("authority file path alias is forbidden")
        git_commit = str(
            _runtime_git(
                self.repository_root,
                "rev-parse",
                "HEAD",
                unavailable_message="authority file lacks current Git identity",
            )
        ).strip()
        git_blob = str(
            _runtime_git(
                self.repository_root,
                "rev-parse",
                f"{git_commit}:{relative_path}",
                unavailable_message="authority file lacks current Git identity",
            )
        ).strip()
        committed_raw = _runtime_git(
            self.repository_root,
            "show",
            f"{git_commit}:{relative_path}",
            text=False,
            unavailable_message="authority file lacks current Git identity",
        )
        if committed_raw != raw or _git_blob(raw) != git_blob:
            raise IntegrityError("authority file differs from captured Git bytes")
        try:
            serialized = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("authority file is not canonical JSON content") from exc
        if serialized != content:
            raise IntegrityError("authority file content does not match registered content")
        return {
            "content_sha256": content_state["content_sha256"],
            "repository_path": relative_path,
            "git_commit": git_commit,
            "git_blob": git_blob,
            "file_size": len(raw),
            "file_sha256": sha256_hex(raw),
        }

    def _prepare_dossier(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare real dossier admission from replayed accepted authority."""
        expected: AcceptedExpectedSet | None = None
        roots: dict[str, RegisteredRoot] | None = None
        current_revision: int | None = None
        accepted_expected = projection["authorities"].get("dossier_expected_set")
        accepted_paths = projection["authorities"].get("path_registration")
        if accepted_expected and accepted_expected.get("status") == "accepted":
            subject = accepted_expected["subject"]
            expected_value = subject.get("expected_set")
            if isinstance(expected_value, dict):
                expected = AcceptedExpectedSet(
                    **{
                        **expected_value,
                        "members": tuple(DossierMember(**member) for member in expected_value["members"]),
                    }
                )
                current_revision = expected.revision
        if accepted_paths and accepted_paths.get("status") == "accepted":
            path_subject = accepted_paths["subject"]
            root_values = path_subject.get("registered_roots")
            if isinstance(root_values, list):
                if is_portable_path_subject(path_subject):
                    if not root_values:
                        raise IntegrityError("accepted portable path authority has no registered root")
                    observation = accepted_paths.get("file_observation")
                    accepted_binding = accepted_paths.get("portable_physical_binding")
                    if not isinstance(observation, Mapping) or not isinstance(accepted_binding, Mapping):
                        raise IntegrityError("accepted portable path authority lacks physical observation")
                    git_commit = observation.get("git_commit")
                    if not isinstance(git_commit, str) or not git_commit:
                        raise IntegrityError("accepted portable path authority lacks a Git commit")
                    current_binding = self._observe_portable_spec_root(path_subject, git_commit)
                    if current_binding != accepted_binding:
                        raise IntegrityError("accepted portable path authority physical binding differs")
                    root_values = [
                        {
                            **dict(root_values[0]),
                            "registration_hash": current_binding["registration_hash"],
                        }
                    ]
                required_root_fields = {
                    "path",
                    "root_id",
                    "registration_revision",
                    "registration_hash",
                    "authorized",
                }
                if any(
                    not isinstance(value, Mapping)
                    or set(value) != required_root_fields
                    or not isinstance(value.get("root_id"), str)
                    or not value.get("root_id")
                    or not isinstance(value.get("path"), str)
                    or not value.get("path")
                    or not isinstance(value.get("registration_revision"), int)
                    or isinstance(value.get("registration_revision"), bool)
                    or value.get("registration_revision", 0) < 1
                    or not isinstance(value.get("registration_hash"), str)
                    or len(value.get("registration_hash", "")) != 64
                    or value.get("authorized") is not True
                    for value in root_values
                ):
                    raise IntegrityError("accepted path authority contains an invalid registered root")
                path_tokens = self.root_tokens
                if any(value.get("path") not in path_tokens for value in root_values):
                    raise IntegrityError("accepted path authority contains an unconfigured root token")
                roots = {
                    value["root_id"]: RegisteredRoot(
                        root_id=value["root_id"],
                        path=path_tokens[value["path"]],
                        registration_revision=value["registration_revision"],
                        registration_hash=value["registration_hash"],
                        authorized=value["authorized"],
                    )
                    for value in root_values
                }
        if expected is None or roots is None or current_revision is None:
            raise IntegrityError("accepted dossier authority is not active")
        payload = command.envelope["payload"]
        if (
            set(payload) != {"row_id", "dossier_id", "expected_set_id", "candidate_members", "candidate_manifest"}
            or payload.get("row_id") != "OR-028"
            or payload.get("dossier_id") != expected.dossier_id
            or payload.get("expected_set_id") != expected.expected_set_id
            or command.target_stream_id != expected.dossier_id
            or not isinstance(payload.get("candidate_members"), list)
            or not isinstance(payload.get("candidate_manifest"), dict)
        ):
            raise IntegrityError("invalid AdmitResearchDossier command")
        try:
            members = tuple(DossierMember(**member) for member in payload["candidate_members"])
        except (TypeError, ValueError) as exc:
            raise IntegrityError("invalid dossier candidate member") from exc
        try:
            self.schemas.validate(
                "ars://portfolio/research-dossier-manifest",
                payload["candidate_manifest"],
                schema_version="1.0.0",
            )
        except SchemaError as exc:
            raise DossierAdmissionRejected("invalid_research_dossier_manifest") from exc
        prepared = prepare_dossier_admission(
            expected_set=expected,
            current_expected_set_revision=current_revision,
            candidate_members=members,
            candidate_manifest=payload["candidate_manifest"],
            registered_roots=roots,
            existing_identities=frozenset(
                {
                    *({_CATALOGUE_STREAM_ID} if projection["catalogue"] is not None else set()),
                    *projection["source_observations"],
                    *projection["candidates"],
                    *projection["assays"],
                    *projection["spikes"],
                    *projection["decisions"],
                    *projection["reviews"],
                    *projection["dossiers"],
                    *projection["portfolio_objects"],
                    *projection["scopes"],
                    *projection["artefact_streams"],
                    *projection["authority_streams"],
                }
            ),
        )
        result: list[tuple[str, str, dict[str, Any]]] = []
        for event in prepared.events:
            event_type = event["event_type"]
            event_payload = event["payload"]
            stream_id = {
                "ResearchDossierAdmitted": expected.dossier_id,
                "PortfolioObjectRegistered": event_payload.get("record_id"),
                "ScopeDefinitionRegistered": event_payload.get("scope_id"),
            }.get(event_type)
            if not isinstance(stream_id, str):
                raise IntegrityError("dossier event lacks immutable stream identity")
            result.append((event_type, stream_id, event_payload))
        return result

    def _valid_promotion_relation(
        self,
        relation: Any,
        **expected: Any,
    ) -> bool:
        """Validate the accepted schema and exact promotion subject joins."""

        if not isinstance(relation, dict):
            return False
        try:
            self.schemas.validate(
                "ars://portfolio/relation/discovery-promotion",
                relation,
                schema_version="1.0.0",
            )
        except SchemaError:
            return False
        return _promotion_relation_matches(relation, **expected)

    def _valid_revisit_relation(
        self,
        relation: Any,
        **expected: Any,
    ) -> bool:
        """Validate the accepted schema and exact revisit predicate joins."""

        if not isinstance(relation, dict):
            return False
        try:
            self.schemas.validate(
                "ars://portfolio/relation/discovery-revisit",
                relation,
                schema_version="1.0.0",
            )
        except SchemaError:
            return False
        return _revisit_relation_matches(relation, **expected)

    def _valid_spike_execution_relation(
        self,
        relation: Any,
        *,
        candidate: Mapping[str, Any],
        assay: Mapping[str, Any],
        spike: Mapping[str, Any],
        decision_id: Any,
    ) -> bool:
        """Validate the accepted execution subject and current resource identity."""

        if not isinstance(relation, dict):
            return False
        try:
            self.schemas.validate(
                "ars://portfolio/relation/spike-execution-authority",
                relation,
                schema_version="1.0.0",
            )
            operational = replay_control_plane(self._operational_events())
        except (SchemaError, KeyError, TypeError, ValueError):
            return False
        resource_ref = relation.get("resource_ref")
        resource = operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
        return bool(
            isinstance(resource, Mapping)
            and resource.get("status") == "active"
            and resource_ref == _record_ref(resource_ref.get("id"), 1, sha256_hex(canonical_bytes(resource)))
            and _spike_execution_relation_matches(
                relation,
                candidate=candidate,
                assay=assay,
                spike=spike,
                decision_id=decision_id,
                resource=resource,
            )
        )

    def _spec_02_execution_approval(
        self,
        candidate: Mapping[str, Any],
        projection: Mapping[str, Any],
        *,
        events: tuple[dict[str, Any], ...],
        evaluation_time: datetime | None = None,
        owner_published_grant_ids: frozenset[str] | None = None,
    ) -> _Spec02ExecutionAuthority | None:
        """Resolve the durable approval and prepared brief for either SPEC-02 entry mode."""

        return _SpecExecutionAuthorityResolver(
            control_root=self.control_root,
            schemas=self.schemas,
            authority_resolver=self.authority_resolver,
            clock=self.clock,
        ).resolve(
            candidate,
            projection,
            events=events,
            evaluation_time=evaluation_time,
            owner_published_grant_ids=owner_published_grant_ids,
        )

    @staticmethod
    def _spec_02_resource_allowed(approval: Mapping[str, Any], resource_id: object) -> bool:
        limits = approval.get("limits")
        return bool(
            isinstance(limits, Mapping)
            and isinstance(resource_id, str)
            and resource_id in limits.get("resource_ids", ())
        )

    @staticmethod
    def _spec_02_resource_use_allowed(approval: Mapping[str, Any], resource_use: object) -> bool:
        limits = approval.get("limits")
        if not isinstance(limits, Mapping) or not isinstance(resource_use, Mapping):
            return False
        pairs = (
            ("external_cost_gbp", "budget_gbp"),
            ("elapsed_seconds", "wall_time_seconds"),
            ("cpu_seconds", "cpu_seconds"),
            ("peak_memory_bytes", "peak_memory_bytes"),
        )
        return all(
            isinstance(resource_use.get(actual), (int, float))
            and not isinstance(resource_use.get(actual), bool)
            and isinstance(limits.get(limit), (int, float))
            and not isinstance(limits.get(limit), bool)
            and resource_use[actual] <= limits[limit]
            for actual, limit in pairs
        )

    def _spec_02_return_allowed(
        self,
        *,
        command: Command,
        authority: _Spec02ExecutionAuthority,
        spike: Mapping[str, Any],
        events: tuple[dict[str, Any], ...],
        prospective_document: Mapping[str, Any] | None = None,
    ) -> bool:
        document = prospective_document
        if document is None:
            rows: list[Mapping[str, Any]] = []
            for event in events:
                if event.get("event_type") != "ArtefactRegistered":
                    continue
                manifest = event.get("payload", {}).get("manifest")
                if not isinstance(manifest, Mapping) or manifest.get("artefact_type") != "spec_02_return":
                    continue
                relative = manifest.get("relative_path")
                content_sha256 = manifest.get("content_sha256")
                if not isinstance(relative, str) or not isinstance(content_sha256, str):
                    return False
                try:
                    raw = read_contained_regular_file(self.control_root, relative, label="SPEC-02 return artefact")
                    value = json.loads(raw)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    return False
                if isinstance(value, Mapping) and raw == canonical_bytes(value) and sha256_hex(raw) == content_sha256:
                    rows.append(value)
            if len(rows) != 1:
                return False
            document = rows[0]
        try:
            self.schemas.validate("ars://portfolio/spec-operator-return", document, schema_version="1.0.0")
        except SchemaError:
            return False
        relation = spike.get("execution_authority_relation")
        resource_ref = relation.get("resource_ref") if isinstance(relation, Mapping) else None
        producer = document.get("producer")
        embedded = document.get("embedded_artefact")
        try:
            embedded_sha256 = sha256_hex(canonical_bytes(embedded)) if isinstance(embedded, Mapping) else None
        except (TypeError, ValueError):
            return False
        embedded_hashes = [
            item.get("sha256")
            for item in document.get("artifact_hashes", ())
            if isinstance(item, Mapping) and item.get("name") == "embedded_artefact"
        ]
        brief = authority.brief
        expected_response = {
            "brief_artefact_id": brief.get("brief_manifest", {}).get("brief_artefact_id"),
            "brief_manifest_sha256": brief.get("brief_manifest_sha256"),
            "operator_session_id": brief.get("operator_session", {}).get("session_id"),
        }
        payload = command.envelope["payload"]
        return bool(
            document.get("stage") == "SPEC-02"
            and document.get("route_id") == "SPEC-GATE6-RUN-V1"
            and document.get("document_type") == "spec_02_return"
            and document.get("responds_to") == expected_response
            and document.get("sources")
            == [{"name": "accepted-spec-source", "sha256": brief.get("route_source", {}).get("raw_sha256")}]
            and isinstance(producer, Mapping)
            and producer.get("actor_id") == command.actor_id
            and producer.get("relation_sha256") == sha256_hex(canonical_bytes(relation))
            and embedded == payload.get("verdict_artifact")
            and embedded_sha256 == payload.get("verdict_sha256")
            and embedded_hashes == [embedded_sha256]
            and document.get("outcome") == ("PARTIAL" if payload.get("verdict") == "PARTIAL" else "COMPLETE")
            and isinstance(resource_ref, Mapping)
            and self._spec_02_resource_allowed(authority.approval, resource_ref.get("id"))
            and self._spec_02_resource_use_allowed(authority.approval, document.get("resource_use"))
            and _spec_02_pass_rerun_matches(document, payload)
        )

    def _prepare_spike(
        self,
        command: Command,
        projection: dict[str, Any],
        *,
        events: tuple[dict[str, Any], ...] = (),
        prospective_document: Mapping[str, Any] | None = None,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare one Spike lifecycle transition batch."""
        p = command.envelope["payload"]
        row = p.get("row_id")
        candidate_id, spike_id, decision_id, review_id = (
            p.get(k) for k in ("candidate_id", "spike_id", "decision_id", "review_id")
        )
        candidate = projection["candidates"].get(candidate_id)
        spike = projection["spikes"].get(spike_id)
        assay = projection["assays"].get(candidate.get("assay_id")) if isinstance(candidate, dict) else None
        decision = projection["decisions"].get(decision_id)
        ct = command.envelope["command_type"]
        spec_02_approval = (
            self._spec_02_execution_approval(candidate, projection, events=events)
            if isinstance(candidate, Mapping)
            and (ct, row) in _SPEC_02_GATED_TRANSITIONS
            and _is_spec_route_candidate(projection, candidate)
            else None
        )
        spec_02_approved = (
            not _is_spec_route_candidate(projection, candidate) if isinstance(candidate, Mapping) else True
        )
        if isinstance(candidate, Mapping) and _is_spec_route_candidate(projection, candidate):
            spec_02_approved = spec_02_approval is not None

        if (
            isinstance(candidate, Mapping)
            and (ct, row) in _SPEC_02_GATED_TRANSITIONS
            and _is_spec_route_candidate(projection, candidate)
            and not spec_02_approved
        ):
            raise IntegrityError("SPEC-02 live-run approval and operator brief are required")

        def out(*events: tuple[str, str]) -> list[tuple[str, str, dict[str, Any]]]:
            return [(event, stream, deepcopy(p.get("w2_payload", p))) for event, stream in events]

        if (
            ct == "ProposePromotionDecision"
            and row == "OR-012"
            and candidate
            and candidate.get("status") == "assay_scored"
            and isinstance(assay, dict)
            and assay.get("status") == "reviewed"
            and p.get("review_id") == assay.get("review_id")
            and isinstance(projection["reviews"].get(p.get("review_id")), dict)
            and projection["reviews"][p["review_id"]].get("status") == "satisfied"
            and command.target_stream_id == decision_id
            and decision is None
            and not _discovery_identity_exists(projection, decision_id)
            and isinstance(p.get("w2_payload"), dict)
            and p["w2_payload"].get("new_decision_id") == decision_id
            and p["w2_payload"].get("decision_kind") == "design_lock"
            and _valid_promotion_options(p["w2_payload"].get("options"))
            and (
                p["w2_payload"].get("recommendation") != "PROMOTE"
                or assay.get("mechanical_recommendation") == "PROMOTE"
            )
            and self._valid_promotion_relation(
                p.get("promotion_relation"),
                decision_id=decision_id,
                candidate=candidate,
                aggregate_id=assay.get("assay_id"),
                aggregate=assay,
                review=projection["reviews"][p["review_id"]],
                gate="assay_to_spike",
                recommendation=p["w2_payload"].get("recommendation"),
                actor_id=command.actor_id,
            )
        ):
            promotion_payload = {**deepcopy(p), "promotion_gate": "assay_to_spike"}
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionRequested", candidate_id, promotion_payload),
            ]
        if (
            ct == "ResolveDecision"
            and row == "OR-013"
            and decision
            and decision.get("status") == "proposed"
            and decision.get("kind") == "discovery_promotion"
            and candidate
            and candidate.get("status") == "promotion_pending"
            and candidate.get("decision_id") == decision_id
            and candidate.get("promotion_gate") == "assay_to_spike"
            and command.target_stream_id == decision_id
            and isinstance(p.get("w2_payload"), dict)
            and p.get("w2_payload", {}).get("decision_id") == decision_id
            and _decision_resolution_authority_matches(command, p["w2_payload"])
            and p["w2_payload"].get("selected_option") in {"PROMOTE", "PARK", "KILL"}
            and p["w2_payload"]["selected_option"] in decision.get("options", ())
            and (
                p["w2_payload"].get("selected_option") != "PROMOTE"
                or isinstance(assay, Mapping)
                and assay.get("mechanical_recommendation") == "PROMOTE"
            )
        ):
            selected_option = p["w2_payload"]["selected_option"]
            applied_payload = {
                **deepcopy(p),
                "promotion_gate": "assay_to_spike",
                "selected_option": selected_option,
                "next_candidate_state": {
                    "PROMOTE": "spike_planning_authorized",
                    "PARK": "parked",
                    "KILL": "killed",
                }[selected_option],
            }
            return [
                ("DecisionResolved", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionApplied", candidate_id, applied_payload),
            ]
        if (
            ct == "RegisterSpikePlan"
            and row in {"OR-014", "OR-025"}
            and candidate
            and (
                row == "OR-014"
                and candidate.get("status") in {"spike_planning_authorized", "parked"}
                and spec_02_approved
                or row == "OR-025"
                and candidate.get("status") == "spike_retry_authorized"
            )
            and spike is None
            and not _discovery_identity_exists(projection, spike_id)
            and command.target_stream_id == spike_id
            and isinstance(p.get("plan_artifact"), dict)
            and (
                row != "OR-014"
                or not _is_spec_route_candidate(projection, candidate)
                or isinstance(spec_02_approval, _Spec02ExecutionAuthority)
                and _spec_02_plan_contract_matches(p["plan_artifact"], spec_02_approval)
            )
            and self._valid_spike_plan(
                p["plan_artifact"],
                p,
                candidate,
                assay,
                projection["decisions"].get(candidate.get("decision_id")),
            )
            and (
                candidate.get("status") != "parked"
                or _parked_candidate_test_plan_matches(
                    candidate,
                    projection["decisions"].get(candidate.get("decision_id")),
                    p,
                )
            )
        ):
            if row == "OR-025":
                old_spike_id = p.get("old_spike_id")
                old_spike = projection["spikes"].get(old_spike_id)
                if (
                    not isinstance(old_spike, dict)
                    or old_spike.get("status") != "retry_authorized"
                    or candidate.get("spike_id") != old_spike_id
                ):
                    raise IntegrityError("invalid Spike retry transition")
                return out(
                    ("SpikePlanned", spike_id),
                    ("SpikeApprovalRequested", spike_id),
                    ("SpikeSuperseded", old_spike_id),
                    ("CandidateSpikeRetryStarted", candidate_id),
                )
            return out(
                ("SpikePlanned", spike_id),
                ("SpikeApprovalRequested", spike_id),
                ("CandidateSpikePlanLinked", candidate_id),
            )
        if (
            ct == "ProposeSpikeExecutionDecision"
            and row == "OR-015"
            and spike
            and spike.get("status") == "approval_pending"
            and spike.get("candidate_id") == candidate_id
            and command.target_stream_id == decision_id
            and decision is None
            and spec_02_approved
            and not _discovery_identity_exists(projection, decision_id)
            and isinstance(p.get("w2_payload"), dict)
            and p["w2_payload"].get("new_decision_id") == decision_id
            and _valid_spike_execution_proposal(p["w2_payload"])
            and isinstance(assay, dict)
            and self._valid_spike_execution_relation(
                p.get("execution_authority_relation"),
                candidate=candidate,
                assay=assay,
                spike=spike,
                decision_id=decision_id,
            )
            and (
                not _is_spec_route_candidate(projection, candidate)
                or isinstance(spec_02_approval, _Spec02ExecutionAuthority)
                and self._spec_02_resource_allowed(
                    spec_02_approval.approval,
                    p.get("execution_authority_relation", {}).get("resource_ref", {}).get("id"),
                )
            )
        ):
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("SpikeExecutionDecisionRequested", spike_id, deepcopy(p)),
            ]
        if (
            ct == "ResolveDecision"
            and row == "OR-016"
            and decision
            and decision.get("status") == "proposed"
            and spike
            and spike.get("decision_id") == decision_id
            and spike.get("candidate_id") == candidate_id
            and candidate
            and candidate.get("status") == "spike_approval_pending"
            and spec_02_approved
            and command.target_stream_id == decision_id
            and isinstance(p.get("w2_payload"), dict)
            and p.get("w2_payload", {}).get("decision_id") == decision_id
            and _decision_resolution_authority_matches(command, p["w2_payload"])
            and p.get("w2_payload", {}).get("selected_option") == "approve"
            and p["w2_payload"]["selected_option"] in decision.get("options", ())
            and p.get("execution_authority_relation") == spike.get("execution_authority_relation")
            and spike.get("execution_authority_relation", {}).get("actor_id") == command.actor_id
            and self._valid_spike_execution_relation(
                p.get("execution_authority_relation"),
                candidate=candidate,
                assay=assay,
                spike=spike,
                decision_id=decision_id,
            )
            and (
                not _is_spec_route_candidate(projection, candidate)
                or isinstance(spec_02_approval, _Spec02ExecutionAuthority)
                and self._spec_02_resource_allowed(
                    spec_02_approval.approval,
                    p.get("execution_authority_relation", {}).get("resource_ref", {}).get("id"),
                )
            )
        ):
            return [
                ("DecisionResolved", decision_id, deepcopy(p["w2_payload"])),
                ("SpikeAuthorized", spike_id, deepcopy(p)),
                ("CandidateSpikeAuthorized", candidate_id, deepcopy(p)),
            ]
        if (
            ct == "StartSpike"
            and row == "OR-017"
            and spike
            and spike.get("status") == "authorized"
            and spike.get("candidate_id") == candidate_id
            and candidate
            and candidate.get("status") == "spike_authorized"
            and spec_02_approved
            and command.target_stream_id == spike_id
            and isinstance(p.get("attempt_id"), str)
            and isinstance(p.get("attempt_sha256"), str)
            and len(p["attempt_sha256"]) == 64
            and isinstance(p.get("lease_id"), str)
            and _spike_execution_ids_available(
                projection["spikes"],
                spike_id,
                p.get("attempt_id"),
                p.get("lease_id"),
            )
            and self._valid_live_spike_lease(p, command)
            and (
                not _is_spec_route_candidate(projection, candidate)
                or isinstance(spec_02_approval, _Spec02ExecutionAuthority)
                and self._spec_02_resource_allowed(spec_02_approval.approval, p.get("resource_grant_id"))
            )
            and isinstance(spike.get("execution_authority_relation"), Mapping)
            and spike["execution_authority_relation"].get("resource_ref", {}).get("id") == p.get("resource_grant_id")
        ):
            operational = replay_control_plane(self._operational_events())
            lease = operational.stream_states.get(p.get("lease_id"))
            if not isinstance(lease, Mapping):
                raise IntegrityError("invalid Spike transition")
            start_payload = {
                **deepcopy(p),
                "lease_sha256": sha256_hex(canonical_bytes(lease)),
                "execution_authority_relation": deepcopy(spike["execution_authority_relation"]),
            }
            return [
                ("SpikeStarted", spike_id, deepcopy(start_payload)),
                ("CandidateSpikeStarted", candidate_id, deepcopy(start_payload)),
            ]
        if (
            ct == "RecordSpikeVerdict"
            and row in {"OR-018", "OR-019"}
            and spike
            and spike.get("status") == "running"
            and spike.get("candidate_id") == candidate_id
            and candidate
            and candidate.get("status") == "spike_running"
            and command.target_stream_id == spike_id
            and spec_02_approved
            and (
                not _is_spec_route_candidate(projection, candidate)
                or (
                    isinstance(spec_02_approval, _Spec02ExecutionAuthority)
                    and self._spec_02_return_allowed(
                        command=command,
                        authority=spec_02_approval,
                        spike=spike,
                        events=events,
                        prospective_document=prospective_document,
                    )
                )
            )
            and isinstance(p.get("verdict_artifact"), dict)
            and self._valid_spike_verdict(p["verdict_artifact"], p, candidate, assay, spike, projection)
        ):
            if (p.get("verdict") == "PARTIAL") != (row == "OR-019"):
                raise IntegrityError("invalid Spike transition")
            if row == "OR-019":
                attempt, lease = self._live_spike_operational_pair(spike, require_unexpired=True)
                now = self.clock()
                if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                    raise IntegrityError("Discovery operational clock must return an aware datetime")
                artifact = p["verdict_artifact"]
                closure_payload = {
                    **deepcopy(p),
                    "attempt_id": spike.get("attempt_id"),
                    "lease_id": spike.get("lease_id"),
                }
                return [
                    ("SpikePartialRecorded", spike_id, deepcopy(p)),
                    (
                        "PartialOutcomeRecorded",
                        str(attempt["attempt_id"]),
                        {
                            "attempt_id": attempt["attempt_id"],
                            "completed_obligations": [artifact["completed_scope"]],
                            "unmet_obligations": [artifact["unmet_scope"]],
                            "candidate_artefact_ids": [p["verdict_sha256"]],
                            "stop_cause": "spike_partial",
                            "restrictions": list(
                                dict.fromkeys([*artifact["limitations"], *artifact["prohibited_inferences"]])
                            ),
                            "subject_kind": "attempt",
                        },
                    ),
                    (
                        "LeaseReleased",
                        str(lease["lease_id"]),
                        {
                            "lease_id": lease["lease_id"],
                            "release_reason": "spike_partial",
                            "holder_actor_id": lease["holder_actor_id"],
                            "observed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                        },
                    ),
                    ("SpikeAttemptClosed", spike_id, closure_payload),
                    ("SpikeLeaseReleased", spike_id, deepcopy(closure_payload)),
                    ("CandidateSpikePartialLinked", candidate_id, deepcopy(p)),
                ]
            attempt, lease = self._live_spike_operational_pair(spike, require_unexpired=True)
            now = self.clock()
            if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                raise IntegrityError("Discovery operational clock must return an aware datetime")
            artifact = p["verdict_artifact"]
            candidate_artefact_ids = list(
                dict.fromkeys(
                    item["id"]
                    for item in artifact["artefact_refs"]
                    if isinstance(item, Mapping) and isinstance(item.get("id"), str)
                )
            )
            if not candidate_artefact_ids:
                raise IntegrityError("invalid Spike operational closure")
            completion_payload = {
                "attempt_id": attempt["attempt_id"],
                "end_evidence_refs": [f"spike-verdict-sha256:{p['verdict_sha256']}"],
                "candidate_artefact_ids": candidate_artefact_ids,
                "output_disposition": "retained_as_candidate" if p.get("verdict") == "PASS" else "quarantined",
            }
            closure_payload = {
                **deepcopy(p),
                "attempt_id": spike.get("attempt_id"),
                "lease_id": spike.get("lease_id"),
            }
            return [
                ("SpikeVerdictRecorded", spike_id, deepcopy(p)),
                ("AttemptCompleted", str(attempt["attempt_id"]), completion_payload),
                (
                    "LeaseReleased",
                    str(lease["lease_id"]),
                    {
                        "lease_id": lease["lease_id"],
                        "release_reason": "spike_complete",
                        "holder_actor_id": lease["holder_actor_id"],
                        "observed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                    },
                ),
                ("SpikeAttemptClosed", spike_id, closure_payload),
                ("SpikeLeaseReleased", spike_id, deepcopy(closure_payload)),
                ("CandidateSpikeVerdictLinked", candidate_id, deepcopy(p)),
            ]
        if ct == "CancelDiscoveryEvaluation" and row == "OR-022":
            artifact = p.get("cancellation_artifact")
            if (
                not isinstance(spike, dict)
                or spike.get("status") not in {"planned", "approval_pending", "authorized", "running"}
                or spike.get("candidate_id") != candidate_id
                or not isinstance(candidate, dict)
                or candidate.get("status") not in {"spike_approval_pending", "spike_authorized", "spike_running"}
                or command.target_stream_id != spike_id
                or p.get("evaluation_kind") != "spike"
                or not isinstance(artifact, dict)
                or not _spike_cancellation_matches(
                    artifact,
                    payload=p,
                    candidate=candidate,
                    spike=spike,
                    decision=projection["decisions"].get(spike.get("decision_id")),
                    state=projection,
                )
            ):
                raise IntegrityError("invalid Spike cancellation transition")
            prepared: list[tuple[str, str, dict[str, Any]]] = []
            execution_decision = projection["decisions"].get(spike.get("decision_id"))
            if isinstance(execution_decision, dict) and execution_decision.get("status") == "proposed":
                prepared.append(
                    (
                        "SpikeExecutionProposalSupersededByCancellation",
                        str(spike["decision_id"]),
                        {
                            "candidate_id": candidate_id,
                            "spike_id": spike_id,
                            "decision_id": spike["decision_id"],
                            "cancellation_sha256": p["cancellation_sha256"],
                        },
                    )
                )
            prepared.append(("SpikeCancelled", spike_id, deepcopy(p)))
            if spike.get("status") == "running":
                attempt, lease = self._live_spike_operational_pair(spike)
                now = self.clock()
                if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                    raise IntegrityError("Discovery operational clock must return an aware datetime")
                prepared.extend(
                    [
                        (
                            "PartialOutcomeRecorded",
                            str(attempt["attempt_id"]),
                            {
                                "attempt_id": attempt["attempt_id"],
                                "completed_obligations": list(artifact.get("completed_scope", [])),
                                "unmet_obligations": list(artifact.get("unmet_scope", ["cancelled"])),
                                "candidate_artefact_ids": [p["cancellation_sha256"]],
                                "stop_cause": "discovery_evaluation_cancelled",
                                "restrictions": list(artifact.get("restrictions", ["no_promotion"])),
                                "subject_kind": "attempt",
                            },
                        ),
                        (
                            "LeaseReleased",
                            str(lease["lease_id"]),
                            {
                                "lease_id": lease["lease_id"],
                                "release_reason": "discovery_evaluation_cancelled",
                                "holder_actor_id": lease["holder_actor_id"],
                                "observed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                            },
                        ),
                        (
                            "SpikeAttemptClosed",
                            spike_id,
                            {**deepcopy(p), "attempt_id": spike.get("attempt_id"), "lease_id": spike.get("lease_id")},
                        ),
                        (
                            "SpikeLeaseReleased",
                            spike_id,
                            {**deepcopy(p), "attempt_id": spike.get("attempt_id"), "lease_id": spike.get("lease_id")},
                        ),
                    ]
                )
            prepared.append(("CandidateEvaluationCancelled", candidate_id, deepcopy(p)))
            return prepared
        spike_review_subject = (
            spike.get("outcome_sha256")
            if row in {"OR-040", "OR-041"} and isinstance(spike, dict)
            else spike.get("verdict_sha256")
            if isinstance(spike, dict)
            else None
        )
        prior_spike_review = projection["reviews"].get(spike.get("review_id")) if isinstance(spike, dict) else None
        spike_supersession = p.get("review_subject_supersession")
        spike_review_contract = p.get("review_contract")
        valid_spike_review_relation = bool(
            isinstance(spike, dict)
            and isinstance(spike_review_contract, Mapping)
            and (
                (spike.get("review_id") is None and spike_supersession is None)
                or _valid_review_supersession(
                    spike_supersession,
                    prior_spike_review,
                    p.get("subject_sha256"),
                    spike_review_contract.get("required_evidence_refs"),
                )
            )
        )
        if (
            ct == "RequestDiscoveryOutcomeReview"
            and row in {"OR-036", "OR-037", "OR-040"}
            and spike
            and spike.get("status")
            == {"OR-036": "verdict_recorded", "OR-037": "partial_recorded", "OR-040": "cancelled"}[row]
            and spike.get("candidate_id") == candidate_id
            and command.target_stream_id == review_id
            and not _discovery_identity_exists(projection, review_id)
            and valid_spike_review_relation
            and (
                p.get("subject_sha256") == spike_review_subject
                or isinstance(spike_supersession, Mapping)
                and spike_supersession.get("prior_subject_sha256") == spike_review_subject
            )
            and spike_review_contract.get("new_review_id") == review_id
            and spike_review_contract.get("subject_ids") == [spike_id]
            and spike_review_contract.get("subject_hashes") == [p.get("subject_sha256")]
        ):
            return [
                ("ReviewRequested", review_id, deepcopy(p["review_contract"])),
                (
                    {
                        "OR-036": "SpikeReviewRequested",
                        "OR-037": "SpikePartialReviewRequested",
                        "OR-040": "SpikeCancellationReviewRequested",
                    }[row],
                    spike_id,
                    deepcopy(p),
                ),
            ]
        if (
            ct == "ReviewDiscoveryOutcome"
            and row in {"OR-020", "OR-021", "OR-041"}
            and spike
            and spike.get("review_pending")
            and spike.get("review_id") == review_id
            and spike.get("candidate_id") == candidate_id
            and projection["reviews"].get(review_id, {}).get("status") == "pending"
            and command.target_stream_id == review_id
            and p.get("subject_sha256") == projection["reviews"][review_id].get("subject_sha256")
            and isinstance(p.get("review_verdict"), dict)
            and p["review_verdict"].get("review_id") == review_id
            and p["review_verdict"].get("reviewer_actor_id") == command.actor_id
            and projection["reviews"][review_id].get("request_actor_id") != command.actor_id
            and spike.get("producer_actor_id") != command.actor_id
            and p["review_verdict"].get("computed_independence_grade")
            == projection["reviews"][review_id].get("required_independence_grade")
            and p["review_verdict"].get("verdict") in projection["reviews"][review_id].get("allowed_verdicts", ())
            and p.get("review_verdict", {}).get("unchanged_subject_sha256")
            == projection["reviews"][review_id].get("subject_sha256")
        ):
            prepared = [("ReviewVerdictRecorded", review_id, deepcopy(p["review_verdict"]))]
            if _review_policy_status(p["review_verdict"]) == "satisfied":
                if row == "OR-020" and spike.get("status") == "verdict_recorded":
                    prepared.append(("SpikeReviewed", spike_id, deepcopy(p)))
                elif row == "OR-021" and spike.get("status") == "partial_recorded":
                    prepared.extend(
                        [
                            ("SpikePartialReviewed", spike_id, deepcopy(p)),
                            ("CandidateSpikePartialReviewed", candidate_id, deepcopy(p)),
                        ]
                    )
                elif row == "OR-041" and spike.get("status") == "cancelled":
                    prepared.extend(
                        [
                            ("SpikeCancellationReviewed", spike_id, deepcopy(p)),
                            ("CandidateSpikeCancellationReviewed", candidate_id, deepcopy(p)),
                        ]
                    )
                else:
                    raise IntegrityError("invalid Spike review row binding")
            return prepared
        if (
            ct == "ProposePromotionDecision"
            and row == "OR-026"
            and isinstance(candidate, dict)
            and candidate.get("status") == "spike_verdict_recorded"
            and candidate.get("spike_id") == spike_id
            and isinstance(spike, dict)
            and spike.get("status") == "reviewed"
            and spike.get("candidate_id") == candidate_id
            and p.get("verdict_sha256") == spike.get("verdict_sha256")
            and p.get("review_id") == spike.get("review_id")
            and projection["reviews"].get(p.get("review_id"), {}).get("status") == "satisfied"
            and command.target_stream_id == decision_id
            and decision is None
            and not _discovery_identity_exists(projection, decision_id)
            and isinstance(p.get("w2_payload"), dict)
            and _valid_spike_promotion_option(spike, p["w2_payload"].get("recommendation"))
            and p["w2_payload"].get("new_decision_id") == decision_id
            and p["w2_payload"].get("decision_kind") == "design_lock"
            and _valid_promotion_options(p["w2_payload"].get("options"))
            and self._valid_promotion_relation(
                p.get("promotion_relation"),
                decision_id=decision_id,
                candidate=candidate,
                aggregate_id=spike_id,
                aggregate=spike,
                review=projection["reviews"][p["review_id"]],
                gate="spike_to_preregistration",
                recommendation=p["w2_payload"].get("recommendation"),
                actor_id=command.actor_id,
            )
        ):
            promotion_payload = {**deepcopy(p), "promotion_gate": "spike_to_preregistration"}
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionRequested", candidate_id, promotion_payload),
            ]
        if (
            ct == "ResolveDecision"
            and row == "OR-027"
            and isinstance(decision, dict)
            and decision.get("status") == "proposed"
            and decision.get("kind") == "discovery_promotion"
            and isinstance(candidate, dict)
            and candidate.get("status") == "promotion_pending"
            and candidate.get("promotion_gate") == "spike_to_preregistration"
            and candidate.get("decision_id") == decision_id
            and candidate.get("spike_id") == spike_id
            and isinstance(spike, dict)
            and spike.get("status") == "reviewed"
            and spike.get("candidate_id") == candidate_id
            and p.get("verdict_sha256") == spike.get("verdict_sha256")
            and p.get("review_id") == spike.get("review_id")
            and command.target_stream_id == decision_id
            and isinstance(p.get("w2_payload"), dict)
            and _valid_spike_promotion_option(spike, p["w2_payload"].get("selected_option"))
            and p["w2_payload"].get("decision_id") == decision_id
            and _decision_resolution_authority_matches(command, p["w2_payload"])
            and p["w2_payload"].get("selected_option") in {"PROMOTE", "PARK", "KILL"}
            and p["w2_payload"]["selected_option"] in decision.get("options", ())
        ):
            selected_option = p["w2_payload"]["selected_option"]
            applied_payload = {
                **deepcopy(p),
                "promotion_gate": "spike_to_preregistration",
                "selected_option": selected_option,
                "next_candidate_state": {
                    "PROMOTE": "preregistration_authorized",
                    "PARK": "parked",
                    "KILL": "killed",
                }[selected_option],
            }
            return [
                ("DecisionResolved", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionApplied", candidate_id, applied_payload),
            ]
        if ct == "ProposeRevisitDecision" and row == "OR-023":
            review = projection["reviews"].get(p.get("review_id"))
            if (
                not isinstance(spike, dict)
                or spike.get("status") not in {"reviewed", "partial_reviewed", "cancellation_reviewed", "parked"}
                or spike.get("candidate_id") != candidate_id
                or spike.get("review_id") != p.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not isinstance(candidate, dict)
                or candidate.get("status") not in {"spike_revisit_eligible", "parked"}
                or _discovery_identity_exists(projection, decision_id)
                or command.target_stream_id != decision_id
                or not _valid_revisit_proposal(p.get("w2_payload"), p.get("review_id"))
                or p["w2_payload"].get("new_decision_id") != decision_id
                or not self._valid_revisit_relation(
                    p.get("revisit_relation"),
                    decision_id=decision_id,
                    candidate=candidate,
                    aggregate_id=spike_id,
                    aggregate=spike,
                    review=review,
                    observations=projection["source_observations"],
                    recommendation=p["w2_payload"].get("recommendation"),
                    actor_id=command.actor_id,
                )
            ):
                raise IntegrityError("invalid Spike revisit proposal")
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("SpikeRevisitRequested", spike_id, deepcopy(p)),
                ("CandidateSpikeRevisitRequested", candidate_id, deepcopy(p)),
            ]
        if ct == "ResolveDecision" and row == "OR-024":
            w2_payload = p.get("w2_payload")
            if (
                not isinstance(w2_payload, dict)
                or w2_payload.get("decision_id") != decision_id
                or not _decision_resolution_authority_matches(command, w2_payload)
                or w2_payload.get("selected_option") not in {"RETRY", "PARK", "KILL"}
                or not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or w2_payload.get("selected_option") not in decision.get("options", ())
                or not isinstance(spike, dict)
                or spike.get("status") != "revisit_pending"
                or spike.get("candidate_id") != candidate_id
                or spike.get("decision_id") != decision_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "spike_revisit_pending"
                or candidate.get("decision_id") != decision_id
                or command.target_stream_id != decision_id
            ):
                raise IntegrityError("invalid Spike revisit resolution")
            resolved_payload = {**deepcopy(p), "selected_option": w2_payload["selected_option"]}
            return [
                ("DecisionResolved", decision_id, deepcopy(w2_payload)),
                ("SpikeRevisitResolved", spike_id, deepcopy(resolved_payload)),
                ("CandidateSpikeRevisitResolved", candidate_id, deepcopy(resolved_payload)),
            ]
        raise IntegrityError(f"invalid Spike transition: {ct}/{row}")

    def _valid_live_spike_lease(self, payload: dict[str, Any], command: Command) -> bool:
        """Resolve the current operational Attempt/Lease relation under the shared writer lock."""
        state = replay_control_plane(self._operational_events())
        attempt = state.stream_states.get(payload.get("attempt_id"))
        lease = state.stream_states.get(payload.get("lease_id"))
        if not isinstance(lease, dict):
            return False
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise IntegrityError("Discovery operational clock must return an aware datetime")
        try:
            expires_at = datetime.fromisoformat(str(lease.get("expires_at")).replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise IntegrityError("invalid operational lease expiry") from exc
        return bool(
            isinstance(attempt, dict)
            and attempt.get("status") == "running"
            and payload.get("attempt_sha256") == sha256_hex(canonical_bytes(attempt))
            and attempt.get("lease_id") == payload.get("lease_id")
            and isinstance(lease, dict)
            and lease.get("status") == "active"
            and lease.get("attempt_id") == payload.get("attempt_id")
            and lease.get("holder_actor_id") == command.actor_id
            and expires_at > now.astimezone(UTC)
            and payload.get("resource_grant_id") == lease.get("resource_grant_id")
        )

    def _live_spike_operational_pair(
        self,
        spike: Mapping[str, Any],
        *,
        require_unexpired: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return the exact current running Attempt and active Lease for a Spike."""

        try:
            state = replay_control_plane(self._operational_events())
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("invalid operational Attempt or Lease history") from exc
        attempt = state.stream_states.get(spike.get("attempt_id"))
        lease = state.stream_states.get(spike.get("lease_id"))
        if (
            not isinstance(attempt, dict)
            or attempt.get("status") != "running"
            or sha256_hex(canonical_bytes(attempt)) != spike.get("attempt_sha256")
            or attempt.get("lease_id") != spike.get("lease_id")
            or not isinstance(lease, dict)
            or lease.get("status") != "active"
            or lease.get("attempt_id") != spike.get("attempt_id")
        ):
            raise IntegrityError("invalid Spike operational closure")
        if require_unexpired:
            now = self.clock()
            if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                raise IntegrityError("Discovery operational clock must return an aware datetime")
            try:
                expires_at = datetime.fromisoformat(str(lease.get("expires_at")).replace("Z", "+00:00"))
            except (AttributeError, TypeError, ValueError) as exc:
                raise IntegrityError("invalid operational lease expiry") from exc
            if expires_at <= now.astimezone(UTC):
                raise IntegrityError("invalid Spike operational closure")
        return attempt, lease

    def _operational_events(self) -> tuple[dict[str, Any], ...]:
        """Select canonical control-plane events from the shared atomic ledger."""

        events = self.operational_ledger.snapshot().events
        resolve_transaction_ids = discovery_resolve_transaction_ids(events)
        return tuple(
            event
            for event in events
            if _shared_event_partition(event, resolve_transaction_ids=resolve_transaction_ids) == "operational"
        )

    def _valid_spike_plan(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any] | None,
        promotion_decision: dict[str, Any] | None,
    ) -> bool:
        """Validate and bind the exact Spike plan used by later evidence."""

        try:
            self.schemas.validate("ars://portfolio/spike-plan", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Spike plan artifact") from exc
        return _spike_plan_matches(artifact, payload, candidate, assay, promotion_decision)

    def _valid_spike_verdict(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any] | None,
        spike: dict[str, Any],
        projection: dict[str, Any],
    ) -> bool:
        """Validate exact evidence relationships and the PASS/FAIL truth table."""

        try:
            self.schemas.validate("ars://portfolio/spike-verdict", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Spike verdict artifact") from exc
        if not isinstance(assay, dict):
            return False
        artefact_streams: dict[str, dict[str, Any]] = {}
        events = self.operational_ledger.snapshot().events
        resolve_transaction_ids = discovery_resolve_transaction_ids(events)
        for event in events:
            if _shared_event_partition(event, resolve_transaction_ids=resolve_transaction_ids) != "artefact":
                continue
            stream_id = event.get("stream_id")
            if not isinstance(stream_id, str):
                return False
            try:
                artefact_streams[stream_id] = reduce_artefact(artefact_streams.get(stream_id, {}), event)
            except (KeyError, TypeError, ValueError):
                return False
        return _spike_verdict_matches(artifact, payload, candidate, assay, spike, projection, artefact_streams)

    def _prepare_assay(self, command: Command, projection: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare one Assay lifecycle transition batch."""
        payload = command.envelope["payload"]
        candidate_id = payload.get("candidate_id")
        assay_id = payload.get("assay_id")
        review_id = payload.get("review_id")
        candidate = projection["candidates"].get(candidate_id)
        assay = projection["assays"].get(assay_id)
        review = projection["reviews"].get(review_id)
        command_type = command.envelope["command_type"]
        if command_type == "RequestAssay":
            route_sha256, spec_01_sha256 = self._current_assay_spec_source_hashes()
            bar = projection["assay_bar_authority"]
            bar_contents = bar.get("contents") if isinstance(bar, Mapping) else None
            rubric_state = bar_contents.get("rubric") if isinstance(bar_contents, Mapping) else None
            scope_state = bar_contents.get("scope") if isinstance(bar_contents, Mapping) else None
            rubric_content = rubric_state.get("content") if isinstance(rubric_state, Mapping) else None
            scope_content = scope_state.get("content") if isinstance(scope_state, Mapping) else None
            current_bar_sources = _assay_content_matches_current_spec_sources(
                rubric_content,
                kind="rubric",
                route_sha256=route_sha256,
                spec_01_sha256=spec_01_sha256,
            ) and _assay_content_matches_current_spec_sources(
                scope_content,
                kind="scope",
                route_sha256=route_sha256,
                spec_01_sha256=spec_01_sha256,
            )
            if payload.get("row_id") == "OR-011":
                old_assay_id = payload.get("old_assay_id")
                old_assay = projection["assays"].get(old_assay_id)
                bar = projection["assay_bar_authority"]
                producer_ref = bar.get("prospective_producer_ref") if isinstance(bar, dict) else None
                if (
                    command.target_stream_id != assay_id
                    or not isinstance(assay_id, str)
                    or assay is not None
                    or _discovery_identity_exists(projection, assay_id)
                    or not isinstance(old_assay, dict)
                    or old_assay.get("status") != "retry_authorized"
                    or not isinstance(candidate, dict)
                    or candidate.get("status") != "assay_retry_authorized"
                    or candidate.get("assay_id") != old_assay_id
                    or payload.get("candidate_revision") != candidate.get("revision")
                    or payload.get("candidate_sha256") != candidate.get("content_sha256")
                    or bar.get("status") != "accepted"
                    or not current_bar_sources
                    or payload.get("assay_bar_acceptance_sha256") != bar.get("acceptance_sha256")
                    or payload.get("producer_relation_sha256") != bar.get("producer_relation_sha256")
                    or not isinstance(producer_ref, dict)
                    or not isinstance(producer_ref.get("id"), str)
                ):
                    raise IntegrityError("invalid RequestAssay retry transition")
                retry_payload = {**deepcopy(payload), "producer_actor_id": producer_ref["id"]}
                return [
                    ("AssayRequested", assay_id, deepcopy(retry_payload)),
                    ("AssayEvidenceCollectionOpened", assay_id, deepcopy(retry_payload)),
                    ("AssaySuperseded", old_assay_id, deepcopy(retry_payload)),
                    ("CandidateAssayRetryStarted", candidate_id, deepcopy(retry_payload)),
                ]
            producer_ref = bar.get("prospective_producer_ref") if isinstance(bar, dict) else None
            if (
                payload.get("row_id") != "OR-003"
                or command.target_stream_id != assay_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "registered"
                or candidate.get("revision") != payload.get("candidate_revision")
                or candidate.get("content_sha256") != payload.get("candidate_sha256")
                or assay is not None
                or _discovery_identity_exists(projection, assay_id)
                or bar.get("status") != "accepted"
                or not current_bar_sources
                or payload.get("assay_bar_acceptance_sha256") != bar.get("acceptance_sha256")
                or payload.get("producer_relation_sha256") != bar.get("producer_relation_sha256")
                or not isinstance(producer_ref, dict)
                or not isinstance(producer_ref.get("id"), str)
            ):
                raise IntegrityError("invalid RequestAssay transition")
            request_payload = {**deepcopy(payload), "producer_actor_id": producer_ref["id"]}
            return [
                ("AssayRequested", assay_id, deepcopy(request_payload)),
                ("AssayEvidenceCollectionOpened", assay_id, deepcopy(request_payload)),
                ("CandidateAssayRequested", candidate_id, deepcopy(request_payload)),
            ]
        if command_type == "RecordAssayScore":
            if (
                payload.get("row_id") != "OR-004"
                or command.target_stream_id != assay_id
                or not isinstance(assay, dict)
                or assay.get("status") != "evidence_collecting"
                or assay.get("candidate_id") != candidate_id
                or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
                or assay.get("producer_actor_id") != command.actor_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_pending"
                or not isinstance(payload.get("scorecard_artifact"), dict)
                or not self._valid_assay_scorecard(
                    payload["scorecard_artifact"],
                    payload,
                    candidate,
                    assay,
                    projection["assay_bar_authority"],
                    command,
                )
            ):
                raise IntegrityError("invalid RecordAssayScore transition")
            return [
                ("AssayScored", assay_id, deepcopy(payload)),
                ("CandidateAssayLinked", candidate_id, deepcopy(payload)),
            ]
        if command_type == "RecordAssayPartial":
            artifact = payload.get("partial_artifact")
            if (
                payload.get("row_id") != "OR-005"
                or command.target_stream_id != assay_id
                or not isinstance(assay, dict)
                or assay.get("status") != "evidence_collecting"
                or assay.get("candidate_id") != candidate_id
                or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
                or assay.get("producer_actor_id") != command.actor_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_pending"
                or not isinstance(artifact, dict)
                or not self._valid_assay_partial(
                    artifact,
                    payload,
                    candidate,
                    assay,
                    projection["assay_bar_authority"],
                )
            ):
                raise IntegrityError("invalid RecordAssayPartial transition")
            return [
                ("AssayPartialRecorded", assay_id, deepcopy(payload)),
                ("CandidateAssayPartialLinked", candidate_id, deepcopy(payload)),
            ]
        if command_type == "CancelDiscoveryEvaluation":
            artifact = payload.get("cancellation_artifact")
            if (
                payload.get("row_id") != "OR-008"
                or command.target_stream_id != assay_id
                or not isinstance(assay, dict)
                or assay.get("status") not in {"requested", "evidence_collecting"}
                or assay.get("candidate_id") != candidate_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_pending"
                or payload.get("evaluation_kind") != "assay"
                or not _assay_cancellation_matches(
                    artifact,
                    payload=payload,
                    candidate=candidate,
                    assay=assay,
                    state=projection,
                )
            ):
                raise IntegrityError("invalid Assay cancellation transition")
            return [
                ("AssayCancelled", assay_id, deepcopy(payload)),
                ("CandidateEvaluationCancelled", candidate_id, deepcopy(payload)),
            ]
        if command_type == "RequestDiscoveryOutcomeReview":
            review_contract = payload.get("review_contract")
            row = payload.get("row_id")
            expected_status = {"OR-034": "scored", "OR-035": "partial_recorded", "OR-038": "cancelled"}.get(row)
            current_subject_sha256 = (
                assay.get("scorecard_sha256")
                if expected_status == "scored" and isinstance(assay, dict)
                else assay.get("outcome_sha256")
                if isinstance(assay, dict)
                else None
            )
            prior_review = projection["reviews"].get(assay.get("review_id")) if isinstance(assay, dict) else None
            supersession = payload.get("review_subject_supersession")
            valid_review_relation = bool(
                isinstance(assay, dict)
                and (
                    (assay.get("review_id") is None and supersession is None)
                    or _valid_review_supersession(
                        supersession,
                        prior_review,
                        payload.get("subject_sha256"),
                        review_contract.get("required_evidence_refs") if isinstance(review_contract, Mapping) else None,
                    )
                )
            )
            if (
                expected_status is None
                or command.target_stream_id != review_id
                or review is not None
                or _discovery_identity_exists(projection, review_id)
                or not isinstance(assay, dict)
                or assay.get("status") != expected_status
                or not valid_review_relation
                or (
                    current_subject_sha256 != payload.get("subject_sha256")
                    and (
                        not isinstance(supersession, Mapping)
                        or supersession.get("prior_subject_sha256") != current_subject_sha256
                    )
                )
                or not isinstance(review_contract, dict)
                or review_contract.get("new_review_id") != review_id
                or review_contract.get("subject_ids") != [assay_id]
                or review_contract.get("subject_hashes") != [payload.get("subject_sha256")]
            ):
                raise IntegrityError("invalid RequestDiscoveryOutcomeReview transition")
            return [
                ("ReviewRequested", review_id, deepcopy(review_contract)),
                (
                    {
                        "OR-034": "AssayOutcomeReviewRequested",
                        "OR-035": "AssayPartialReviewRequested",
                        "OR-038": "AssayCancellationReviewRequested",
                    }[row],
                    assay_id,
                    deepcopy(payload),
                ),
            ]
        if command_type == "ReviewDiscoveryOutcome":
            review_verdict = payload.get("review_verdict")
            row = payload.get("row_id")
            expected_status = {"OR-006": "scored", "OR-007": "partial_recorded", "OR-039": "cancelled"}.get(row)
            expected_candidate_status = {
                "OR-006": "assay_scored",
                "OR-007": "assay_partial_recorded",
                "OR-039": "assay_cancelled",
            }.get(row)
            if (
                expected_status is None
                or command.target_stream_id != review_id
                or not isinstance(review_verdict, dict)
                or review_verdict.get("review_id") != review_id
                or payload.get("verdict") != review_verdict.get("verdict")
                or review_verdict.get("unchanged_subject_sha256") != payload.get("subject_sha256")
                or review_verdict.get("reviewer_actor_id") != command.actor_id
                or not isinstance(review, dict)
                or review.get("status") != "pending"
                or review.get("subject_sha256") != payload.get("subject_sha256")
                or review.get("request_actor_id") == command.actor_id
                or review_verdict.get("verdict") not in review.get("allowed_verdicts", ())
                or review_verdict.get("computed_independence_grade") != review.get("required_independence_grade")
                or not isinstance(assay, dict)
                or assay.get("candidate_id") != candidate_id
                or not assay.get("review_pending")
                or assay.get("review_id") != review_id
                or assay.get("status") != expected_status
                or assay.get("producer_actor_id") == command.actor_id
                or projection["assay_bar_authority"].get("prospective_producer_ref", {}).get("id") == command.actor_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != expected_candidate_status
            ):
                raise IntegrityError("invalid ReviewDiscoveryOutcome transition")
            events = [("ReviewVerdictRecorded", review_id, deepcopy(review_verdict))]
            if _review_policy_status(review_verdict) == "satisfied":
                if row == "OR-006":
                    events.append(("AssayReviewed", assay_id, deepcopy(payload)))
                elif row == "OR-007":
                    events.extend(
                        [
                            ("AssayPartialReviewed", assay_id, deepcopy(payload)),
                            ("CandidateAssayPartialReviewed", candidate_id, deepcopy(payload)),
                        ]
                    )
                else:
                    events.extend(
                        [
                            ("AssayCancellationReviewed", assay_id, deepcopy(payload)),
                            ("CandidateAssayCancellationReviewed", candidate_id, deepcopy(payload)),
                        ]
                    )
            return events
        if command_type == "ProposeRevisitDecision":
            decision_id = payload.get("decision_id")
            review = projection["reviews"].get(payload.get("review_id"))
            if (
                payload.get("row_id") != "OR-009"
                or command.target_stream_id != decision_id
                or _discovery_identity_exists(projection, decision_id)
                or not isinstance(assay, dict)
                or assay.get("status") not in {"reviewed", "partial_reviewed", "cancellation_reviewed", "parked"}
                or assay.get("candidate_id") != candidate_id
                or assay.get("review_id") != payload.get("review_id")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or not isinstance(candidate, dict)
                or candidate.get("status") not in {"assay_revisit_eligible", "parked"}
                or not _valid_revisit_proposal(payload.get("w2_payload"), payload.get("review_id"))
                or payload["w2_payload"].get("new_decision_id") != decision_id
                or not self._valid_revisit_relation(
                    payload.get("revisit_relation"),
                    decision_id=decision_id,
                    candidate=candidate,
                    aggregate_id=assay_id,
                    aggregate=assay,
                    review=review,
                    observations=projection["source_observations"],
                    recommendation=payload["w2_payload"].get("recommendation"),
                    actor_id=command.actor_id,
                )
            ):
                raise IntegrityError("invalid Assay revisit proposal")
            return [
                ("DecisionProposed", decision_id, deepcopy(payload["w2_payload"])),
                ("AssayRevisitRequested", assay_id, deepcopy(payload)),
                ("CandidateAssayRevisitRequested", candidate_id, deepcopy(payload)),
            ]
        if command_type == "ResolveDecision":
            decision_id = payload.get("decision_id")
            w2_payload = payload.get("w2_payload")
            decision = projection["decisions"].get(decision_id)
            if (
                payload.get("row_id") != "OR-010"
                or command.target_stream_id != decision_id
                or not isinstance(w2_payload, dict)
                or w2_payload.get("decision_id") != decision_id
                or not _decision_resolution_authority_matches(command, w2_payload)
                or w2_payload.get("selected_option") not in {"RETRY", "PARK", "KILL"}
                or not isinstance(decision, dict)
                or decision.get("status") != "proposed"
                or w2_payload.get("selected_option") not in decision.get("options", ())
                or not isinstance(assay, dict)
                or assay.get("status") != "revisit_pending"
                or assay.get("candidate_id") != candidate_id
                or assay.get("decision_id") != decision_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_revisit_pending"
                or candidate.get("decision_id") != decision_id
            ):
                raise IntegrityError("invalid Assay revisit resolution")
            resolved_payload = {**deepcopy(payload), "selected_option": w2_payload["selected_option"]}
            return [
                ("DecisionResolved", decision_id, deepcopy(w2_payload)),
                ("AssayRevisitResolved", assay_id, deepcopy(resolved_payload)),
                ("CandidateAssayRevisitResolved", candidate_id, deepcopy(resolved_payload)),
            ]
        raise IntegrityError(f"unsupported Assay command: {command_type}")

    def _valid_assay_scorecard(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any],
        bar: dict[str, Any],
        command: Command,
    ) -> bool:
        """Validate and bind the exact Assay scorecard before publication."""
        try:
            self.schemas.validate("ars://portfolio/assay-scorecard", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Assay scorecard artifact") from exc
        return _assay_scorecard_matches(artifact, payload, candidate, assay, bar, command.actor_id)

    def _valid_assay_partial(
        self,
        artifact: dict[str, Any],
        payload: dict[str, Any],
        candidate: dict[str, Any],
        assay: dict[str, Any],
        bar: dict[str, Any],
    ) -> bool:
        """Validate and bind the exact Assay Partial artifact before publication."""
        try:
            self.schemas.validate("ars://portfolio/assay-partial", artifact, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Assay Partial artifact") from exc
        acceptance = bar.get("acceptance")
        if not isinstance(acceptance, dict):
            return False
        return bool(
            bar.get("status") == "accepted"
            and assay.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
            and _assay_partial_bindings_match(artifact, payload, candidate, assay, bar, acceptance)
        )

    def _prepare_genesis(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Verify and prepare the one-time accepted W11 catalogue import."""
        if projection["catalogue"] is not None:
            raise IntegrityError("W11 genesis already exists")
        if command.target_stream_id != _CATALOGUE_STREAM_ID or command.expected_stream_version != 0:
            raise IntegrityError("W11 genesis stream identity mismatch")
        if command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        try:
            raw = self.catalogue_path.read_bytes()
        except OSError as exc:
            raise IntegrityError("catalogue path is unavailable") from exc
        if (
            len(raw) != _ACCEPTED["catalogue_bytes"]
            or sha256_hex(raw) != _ACCEPTED["catalogue_sha256"]
            or _git_blob(raw) != _ACCEPTED["catalogue_blob"]
        ):
            raise IntegrityError("catalogue identity mismatch")
        repository_root = self.repository_root
        bootstrap = (
            repository_root / ".research-system" / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml"
        )
        try:
            bootstrap_raw = bootstrap.read_bytes()
        except OSError as exc:
            raise IntegrityError("bootstrap contract is unavailable") from exc
        if (
            sha256_hex(bootstrap_raw) != _ACCEPTED["bootstrap_sha256"]
            or _git_blob(bootstrap_raw) != _ACCEPTED["bootstrap_blob"]
        ):
            raise IntegrityError("bootstrap identity mismatch")
        catalogue = json.loads(raw)
        row_ids = tuple(row.get("owner_row_id") for row in catalogue.get("owner_contract_rows", ()))
        if catalogue.get("owner_row_count") != 81 or row_ids != _ROW_IDS or len(set(row_ids)) != 81:
            raise IntegrityError("catalogue row set mismatch")
        _validate_discovery_route_registry(catalogue)
        return "W11CatalogueGenesisImported", _accepted_genesis_payload()

    def _prepare_candidate(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Validate and prepare the thinnest Candidate registration."""
        if projection["catalogue"] is None:
            raise IntegrityError("W11 genesis is required before Candidate registration")
        payload = command.envelope["payload"]
        required = {"candidate_id", "revision", "content_sha256", "source_observation_refs", "title"}
        if set(payload) != required or payload.get("candidate_id") != command.target_stream_id:
            raise IntegrityError("invalid Candidate registration")
        if payload.get("revision") != 1 or not isinstance(payload.get("title"), str) or not payload["title"]:
            raise IntegrityError("invalid Candidate registration")
        digest = payload.get("content_sha256")
        observations = payload.get("source_observation_refs")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not isinstance(observations, list)
            or not observations
            or not all(isinstance(item, str) and item for item in observations)
        ):
            raise IntegrityError("invalid Candidate registration")
        if _discovery_identity_exists(projection, command.target_stream_id):
            raise IntegrityError("Candidate identity collision")
        multiset_hash = _source_observation_multiset_hash(observations, projection["source_observations"])
        if digest != multiset_hash:
            raise IntegrityError("Candidate content hash does not match resolved observations")
        return "CandidateRegistered", {
            **deepcopy(payload),
            "owner_row_id": "OR-001",
            "source_observation_multiset_hash": multiset_hash,
        }

    def _prepare_candidate_supersession(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Prepare the exact OR-002 Candidate supersession relation."""

        payload = command.envelope["payload"]
        if set(payload) != {"row_id", "predecessor_ref", "replacement_ref", "lineage_reason"}:
            raise IntegrityError("invalid Candidate supersession command")
        predecessor_ref = payload.get("predecessor_ref")
        replacement_ref = payload.get("replacement_ref")
        predecessor_id = predecessor_ref.get("id") if isinstance(predecessor_ref, Mapping) else None
        replacement_id = replacement_ref.get("id") if isinstance(replacement_ref, Mapping) else None
        predecessor = projection["candidates"].get(predecessor_id)
        replacement = projection["candidates"].get(replacement_id)
        reason = payload.get("lineage_reason")
        if not isinstance(predecessor, Mapping) or not isinstance(replacement, Mapping):
            raise IntegrityError("invalid Candidate supersession subject")
        if predecessor_id == replacement_id:
            raise IntegrityError("invalid Candidate supersession")
        lineage = _candidate_supersession_lineage(projection["candidates"], predecessor, replacement)
        if (
            payload.get("row_id") != "OR-002"
            or command.target_stream_id != predecessor_id
            or predecessor_id == replacement_id
            or predecessor_ref != _candidate_ref(predecessor)
            or replacement_ref != _candidate_ref(replacement)
            or predecessor.get("status") == "superseded"
            or replacement.get("status") == "superseded"
            or _candidate_replacement_is_used(projection["candidates"], replacement_id)
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise IntegrityError("invalid Candidate supersession")
        lineage_sha256 = sha256_hex(canonical_bytes({"lineage": lineage, "lineage_reason": reason}))
        event_payload = {
            "owner_row_id": "OR-002",
            "predecessor_ref": deepcopy(predecessor_ref),
            "replacement_ref": deepcopy(replacement_ref),
            "lineage_reason": reason,
            "lineage": lineage,
            "lineage_sha256": lineage_sha256,
        }
        return [("CandidateSuperseded", str(predecessor_id), event_payload)]

    def _prepare_scout_observation(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Ingest one exact Scout observation batch and its explicit Candidates."""

        if projection["catalogue"] is None:
            raise IntegrityError("W11 genesis is required before Scout observation ingestion")
        payload = command.envelope["payload"]
        required = {"row_id", "observation_id", "batch", "batch_sha256", "candidate_blueprints"}
        observation_id = payload.get("observation_id")
        batch = payload.get("batch")
        blueprints = payload.get("candidate_blueprints")
        if (
            set(payload) != required
            or payload.get("row_id") != "OR-029"
            or observation_id != command.target_stream_id
            or not isinstance(observation_id, str)
            or not isinstance(batch, dict)
            or not isinstance(blueprints, list)
            or not blueprints
            or _discovery_identity_exists(projection, observation_id)
        ):
            raise IntegrityError("invalid Scout observation ingestion")
        try:
            self.schemas.validate("ars://portfolio/scout-observation-batch", batch, schema_version="1.0.0")
        except SchemaError as exc:
            raise IntegrityError("invalid Scout observation batch") from exc
        batch_sha256 = sha256_hex(canonical_bytes(batch))
        dedup_keys = batch.get("normalized_dedup_keys")
        if (
            payload.get("batch_sha256") != batch_sha256
            or not isinstance(dedup_keys, list)
            or not dedup_keys
            or len(dedup_keys) != len(set(dedup_keys))
            or any(
                set(dedup_keys) & set(existing.get("normalized_dedup_keys", []))
                for existing in projection["source_observations"].values()
            )
        ):
            raise IntegrityError("Scout observation identity or alias collision")
        observed = {
            **projection["source_observations"],
            observation_id: {"content_sha256": batch_sha256, "normalized_dedup_keys": deepcopy(dedup_keys)},
        }
        candidate_events: list[tuple[str, str, dict[str, Any]]] = []
        seen_candidates: set[str] = set()
        for blueprint in blueprints:
            if not isinstance(blueprint, dict):
                raise IntegrityError("invalid Scout Candidate blueprint")
            candidate_id = blueprint.get("candidate_id")
            refs = blueprint.get("source_observation_refs")
            if (
                set(blueprint) != {"candidate_id", "revision", "content_sha256", "source_observation_refs", "title"}
                or not isinstance(candidate_id, str)
                or candidate_id in seen_candidates
                or _discovery_identity_exists(projection, candidate_id)
                or candidate_id == observation_id
                or blueprint.get("revision") != 1
                or not isinstance(blueprint.get("title"), str)
                or not blueprint["title"]
                or not isinstance(refs, list)
                or observation_id not in refs
            ):
                raise IntegrityError("invalid Scout Candidate blueprint")
            multiset_hash = _source_observation_multiset_hash(refs, observed)
            if blueprint.get("content_sha256") != multiset_hash:
                raise IntegrityError("Scout Candidate content hash does not match observations")
            seen_candidates.add(candidate_id)
            candidate_events.append(
                (
                    "CandidateRegistered",
                    candidate_id,
                    {
                        **deepcopy(blueprint),
                        "owner_row_id": "OR-029",
                        "source_observation_multiset_hash": multiset_hash,
                    },
                )
            )
        observation_payload = {
            "row_id": "OR-029",
            "observation_id": observation_id,
            "batch": deepcopy(batch),
            "content_sha256": batch_sha256,
            "normalized_dedup_keys": deepcopy(dedup_keys),
            "candidate_blueprints_sha256": sha256_hex(canonical_bytes(blueprints)),
        }
        return [("ScoutObservationIngested", observation_id, observation_payload), *candidate_events]
