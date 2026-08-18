"""Fail-closed public resolver for canonical artefact consumption."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Protocol

from research_system.artefacts.authority import (
    AcceptedArtefactAuthorityContract,
    ArtefactAuthorityContractLoader,
    GoverningEvidenceResolution,
    GoverningEvidenceResolver,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.decision_identity import decision_semantic_sha256
from research_system.errors import ArsError
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import load_store_manifest_unbound
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore


_INDEPENDENCE_ORDER = {"I0": 0, "I1": 1, "I2": 2, "I3": 3}
_REVIEW_RECORD_FIELDS = {
    "schema_id",
    "schema_version",
    "project_id",
    "review_id",
    "subject_sha256",
    "reviewer_actor_id",
    "eligible",
    "related",
    "independence_grade",
    "status",
}


class ArtefactUseDenied(ArsError):
    """One stable, side-effect-free failure surface for denied consumption."""

    def __init__(self, reason_code: str, explanation: str) -> None:
        super().__init__(explanation)
        self.reason_code = reason_code
        self.explanation = explanation


class ArtefactContentReader(Protocol):
    """Read exact bytes through the configured root-identity boundary."""

    def read(self, *, root_id: str, relative_path: str) -> bytes:
        """Return bytes from one already configured logical root and relative path."""


@dataclass(frozen=True)
class ArtefactUseRequest:
    """Exact subject, consumer, scope, policy, and time of one canonical read."""

    artefact_id: str
    exact_content_sha256: str
    consumer_id: str
    consumer_kind: str
    project_id: str
    task_id: str
    scope_id: str
    predicate_id: str
    predicate_version: str
    predicate_sha256: str
    evaluation_time: datetime
    required_decision_kind: str | None

    def __post_init__(self) -> None:
        textual = (
            self.artefact_id,
            self.consumer_id,
            self.consumer_kind,
            self.project_id,
            self.task_id,
            self.scope_id,
            self.predicate_id,
            self.predicate_version,
        )
        if any(not isinstance(value, str) or not value for value in textual):
            raise ValueError("artefact use request identities must be non-empty strings")
        for label, value in (
            ("exact content SHA-256", self.exact_content_sha256),
            ("predicate SHA-256", self.predicate_sha256),
        ):
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")
        if self.evaluation_time.tzinfo is None or self.evaluation_time.utcoffset() != UTC.utcoffset(
            self.evaluation_time
        ):
            raise ValueError("artefact use evaluation time must be UTC")
        if self.required_decision_kind not in {None, "claim_promotion"}:
            raise ValueError("artefact use decision kind is not closed")


@dataclass(frozen=True)
class ResolvedArtefactEvidence:
    """Immutable evidence returned only after every current authority check passes."""

    artefact_id: str
    exact_content_sha256: str
    consumer_id: str
    consumer_kind: str
    project_id: str
    task_id: str
    scope_id: str
    predicate_id: str
    predicate_version: str
    predicate_sha256: str
    manifest_sha256: str
    authority_event_id: str
    authority_event_hash: str
    governing_review_ids: tuple[str, ...]
    governing_review_record_sha256s: tuple[str, ...]
    governing_review_set_sha256: str
    decision_id: str | None
    decision_event_id: str | None
    decision_event_hash: str | None
    decision_projection_sha256: str | None
    canonical_manifest_bytes: bytes
    content_bytes: bytes
    manifest: Mapping[str, object]


@dataclass(frozen=True)
class _GoverningReviewProof:
    review_ids: tuple[str, ...]
    record_sha256s: tuple[str, ...]
    set_sha256: str


@dataclass(frozen=True)
class _DecisionProof:
    decision_id: str
    event_id: str
    event_hash: str
    projection_sha256: str


def predicate_reference(predicate_id: str, predicate_version: str, predicate_sha256: str) -> str:
    """Return the only accepted schema-compatible predicate reference encoding."""
    return f"{predicate_id}@{predicate_version}#sha256:{predicate_sha256}"


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _deny(code: str, explanation: str) -> None:
    raise ArtefactUseDenied(code, explanation)


def _parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        _deny("decision_invalid", f"{label} is not a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _deny("decision_invalid", f"{label} is not a UTC timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        _deny("decision_invalid", f"{label} is not a UTC timestamp")
    return parsed


class ArtefactUseResolver:
    """Rebuild current replay state and authorize one exact immutable read."""

    def __init__(
        self,
        *,
        ledger: EventLedger,
        objects: ObjectStore,
        schemas: SchemaRegistry,
        contract_loader: ArtefactAuthorityContractLoader,
        governing_evidence: GoverningEvidenceResolver,
        content_reader: ArtefactContentReader,
        authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
        spec_execution_authority_validator_factory: Callable[
            [tuple[dict[str, Any], ...]],
            Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], bool], None],
        ]
        | None = None,
        legacy_command_provenance_through_position: int = 0,
    ) -> None:
        if ledger.schemas is not schemas:
            raise TypeError("artefact use resolver requires the ledger's exact SchemaRegistry")
        if ledger.control_root.resolve(strict=False) != objects.control_root.resolve(strict=False):
            raise ValueError("artefact ledger and object store roots differ")
        self.ledger = ledger
        self.objects = objects
        self.schemas = schemas
        self.contract_loader = contract_loader
        self.governing_evidence = governing_evidence
        self.content_reader = content_reader
        self.authority_state_validator = authority_state_validator
        if spec_execution_authority_validator_factory is not None and not callable(
            spec_execution_authority_validator_factory
        ):
            raise TypeError("SPEC execution authority validator factory must be callable")
        self.spec_execution_authority_validator_factory = spec_execution_authority_validator_factory
        self.legacy_command_provenance_through_position = legacy_command_provenance_through_position

    def resolve(self, request: ArtefactUseRequest) -> ResolvedArtefactEvidence:
        """Resolve current authority or fail with no mutation and no fallback."""
        try:
            return self._resolve(request)
        except ArtefactUseDenied:
            raise
        except Exception as exc:  # noqa: BLE001 - every dependency failure is a denial
            raise ArtefactUseDenied("authority_resolution_failed", "artefact authority could not be resolved") from exc

    def _resolve(self, request: ArtefactUseRequest) -> ResolvedArtefactEvidence:
        if request.project_id != self.ledger.project_id:
            _deny("project_mismatch", "artefact request is foreign to the selected project")
        contract = self.contract_loader.load()
        predicate, accepted_predicate_hash = contract.predicate_for(request.consumer_kind)
        self._validate_predicate_request(request, predicate, accepted_predicate_hash)

        before = self.ledger.snapshot()
        spec_validator = (
            None
            if self.spec_execution_authority_validator_factory is None
            else self.spec_execution_authority_validator_factory(before.events)
        )
        if spec_validator is not None and not callable(spec_validator):
            _deny("authority_resolution_failed", "SPEC execution authority validator is unavailable")
        state = replay(
            before.events,
            schema_registry=self.schemas,
            legacy_command_provenance_through_position=self.legacy_command_provenance_through_position,
            authority_state_validator=self.authority_state_validator,
            spec_execution_authority_validator=spec_validator,
        )
        if state.get("project_id") != request.project_id:
            _deny("project_mismatch", "replay state is foreign to the requested project")
        stream = state.get("streams", {}).get(request.artefact_id)
        if not isinstance(stream, dict) or stream.get("artefact_id") != request.artefact_id:
            _deny("artefact_unregistered", "artefact has no current replay-derived registration")
        if stream.get("content_sha256") != request.exact_content_sha256:
            _deny("subject_hash_mismatch", "artefact content hash differs from the exact requested subject")

        manifest = stream.get("manifest")
        if not isinstance(manifest, dict):
            _deny("manifest_unavailable", "artefact manifest is absent from replay state")
        stored = self.objects.read("artefact", request.artefact_id, 1)
        if not isinstance(stored, dict) or stored != manifest:
            _deny("manifest_substitution", "stored artefact manifest differs from replay authority")
        if (
            manifest.get("artefact_id") != request.artefact_id
            or manifest.get("content_sha256") != request.exact_content_sha256
        ):
            _deny("manifest_subject_mismatch", "artefact manifest does not bind the exact requested subject")
        if manifest.get("task_id") != request.task_id:
            _deny("task_scope_mismatch", "artefact producer task differs from the requested task")
        authority = manifest.get("authority")
        if not isinstance(authority, dict):
            _deny("authority_unavailable", "artefact manifest authority is absent")
        if authority.get("accepted_scope") != request.scope_id:
            _deny("accepted_scope_mismatch", "artefact authority does not cover the exact requested scope")
        restrictions = authority.get("consumer_restrictions")
        if not isinstance(restrictions, list) or request.consumer_id in restrictions:
            _deny("consumer_restricted", "artefact consumer is restricted by the registered manifest")

        event_reference = stream.get("consumer_predicate")
        expected_reference = predicate_reference(
            request.predicate_id,
            request.predicate_version,
            request.predicate_sha256,
        )
        if event_reference != expected_reference:
            _deny("predicate_binding_mismatch", "current use authority binds a different consumer predicate")
        dimensions = self._current_dimensions(authority, stream)
        accepted_dimensions = predicate.get("dimensions")
        if not isinstance(accepted_dimensions, dict) or any(
            value not in accepted_dimensions.get(dimension, []) for dimension, value in dimensions.items()
        ):
            _deny("predicate_not_satisfied", "artefact state does not satisfy every accepted authority dimension")

        governing_reviews = self._validate_governing_reviews(
            request,
            contract,
            stream,
            manifest,
            before,
        )
        decision = self._validate_decision(
            request,
            contract,
            state,
            stream,
            governing_reviews.review_ids,
            before.events,
        )
        authority_event_id = stream.get("authority_event_id")
        authority_event_hash = stream.get("authority_event_hash")
        if not isinstance(authority_event_id, str) or not isinstance(authority_event_hash, str):
            _deny("authority_event_unavailable", "current use authority lacks immutable event evidence")

        root_id = manifest.get("root_id")
        relative_path = manifest.get("relative_path")
        if not isinstance(root_id, str) or not root_id or not isinstance(relative_path, str) or not relative_path:
            _deny("content_location_invalid", "artefact manifest lacks an exact content location")
        content_bytes = self.content_reader.read(root_id=root_id, relative_path=relative_path)
        if not isinstance(content_bytes, bytes):
            _deny("content_unavailable", "artefact content reader did not return immutable bytes")
        if sha256_hex(content_bytes) != request.exact_content_sha256:
            _deny("content_substitution", "resolved artefact bytes differ from the exact requested subject")
        size_bytes = manifest.get("size_bytes")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes != len(content_bytes):
            _deny("content_size_mismatch", "resolved artefact bytes differ from the registered size")

        after = self.ledger.snapshot()
        if (after.global_position, after.event_hash) != (before.global_position, before.event_hash):
            _deny("authority_changed", "artefact authority changed during resolution")
        manifest_bytes = canonical_bytes(manifest)
        frozen = _freeze(manifest)
        if not isinstance(frozen, Mapping):
            _deny("manifest_unavailable", "artefact manifest is not immutable evidence")
        return ResolvedArtefactEvidence(
            artefact_id=request.artefact_id,
            exact_content_sha256=request.exact_content_sha256,
            consumer_id=request.consumer_id,
            consumer_kind=request.consumer_kind,
            project_id=request.project_id,
            task_id=request.task_id,
            scope_id=request.scope_id,
            predicate_id=request.predicate_id,
            predicate_version=request.predicate_version,
            predicate_sha256=request.predicate_sha256,
            manifest_sha256=contract.manifest_sha256,
            authority_event_id=authority_event_id,
            authority_event_hash=authority_event_hash,
            governing_review_ids=governing_reviews.review_ids,
            governing_review_record_sha256s=governing_reviews.record_sha256s,
            governing_review_set_sha256=governing_reviews.set_sha256,
            decision_id=decision.decision_id if decision is not None else None,
            decision_event_id=decision.event_id if decision is not None else None,
            decision_event_hash=decision.event_hash if decision is not None else None,
            decision_projection_sha256=decision.projection_sha256 if decision is not None else None,
            canonical_manifest_bytes=manifest_bytes,
            content_bytes=content_bytes,
            manifest=frozen,
        )

    @staticmethod
    def _validate_predicate_request(
        request: ArtefactUseRequest,
        predicate: Mapping[str, object],
        accepted_predicate_hash: str,
    ) -> None:
        if (
            request.predicate_id != predicate.get("predicate_id")
            or request.predicate_version != predicate.get("predicate_version")
            or request.predicate_sha256 != accepted_predicate_hash
            or request.consumer_id not in predicate.get("allowed_consumer_ids", [])
        ):
            _deny("predicate_identity_mismatch", "request does not bind the accepted predicate and consumer")
        if request.required_decision_kind != predicate.get("required_decision_kind"):
            _deny("decision_kind_mismatch", "request cannot weaken or add the accepted decision requirement")

    @staticmethod
    def _current_dimensions(authority: Mapping[str, object], stream: Mapping[str, object]) -> dict[str, object]:
        reviews = stream.get("scientific_reviews")
        current_review: object = authority.get("scientific_review")
        if isinstance(reviews, list) and reviews:
            latest = reviews[-1]
            if isinstance(latest, dict):
                current_review = latest.get("scientific_review")
        return {
            "availability": stream.get("availability", authority.get("availability")),
            "regenerability": stream.get("regenerability", authority.get("regenerability")),
            "integrity": stream.get("integrity", authority.get("integrity")),
            "structural_validation": stream.get("structural_validation", authority.get("structural_validation")),
            "scientific_review": current_review,
            "use_authority": stream.get("use_authority"),
        }

    def _validate_governing_reviews(
        self,
        request: ArtefactUseRequest,
        contract: AcceptedArtefactAuthorityContract,
        stream: Mapping[str, object],
        manifest: Mapping[str, object],
        snapshot: object,
    ) -> _GoverningReviewProof:
        rule = contract.review_rules_by_kind[request.consumer_kind]
        minimum = rule.get("minimum_approved_reviews")
        minimum_grade = rule.get("minimum_independence_grade")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            _deny("review_rule_invalid", "accepted governing-review count is invalid")
        if minimum_grade not in _INDEPENDENCE_ORDER:
            _deny("review_rule_invalid", "accepted governing-review independence grade is invalid")
        reviews = stream.get("scientific_reviews")
        authority_refs = stream.get("authority_evidence_refs")
        if not isinstance(reviews, list) or not isinstance(authority_refs, list):
            _deny("governing_review_missing", "current authority has no replay-derived governing review set")
        position_refs = [reference for reference in authority_refs if str(reference).startswith("ledger-position:")]
        raw_prefix_refs = [reference for reference in authority_refs if str(reference).startswith("raw-prefix-sha256:")]
        if len(position_refs) != 1 or len(raw_prefix_refs) != 1:
            _deny("review_snapshot_unavailable", "current authority lacks one exact review snapshot binding")
        try:
            bound_position = int(str(position_refs[0]).partition(":")[2])
        except ValueError:
            _deny("review_snapshot_unavailable", "current authority review snapshot position is invalid")
        bound_raw_prefix_sha256 = str(raw_prefix_refs[0]).partition(":")[2]
        if any(
            event.get("event_type") == "ScientificReviewRecorded"
            and event.get("stream_id") == request.artefact_id
            and int(event.get("global_position", 0)) > bound_position
            for event in snapshot.events
        ):
            _deny("governing_review_changed", "governing reviews changed after the accepted authority snapshot")
        producer_actor = manifest.get("producer_actor_id")
        all_review_ids = [
            event.get("payload", {}).get("review_id")
            for event in snapshot.events
            if event.get("event_type") == "ScientificReviewRecorded" and isinstance(event.get("payload"), dict)
        ]
        if len(all_review_ids) != len(set(all_review_ids)):
            _deny("governing_review_duplicate", "scientific review identity is duplicated in verified replay")
        rows: list[dict[str, object]] = []
        census_rows: list[dict[str, object]] = []
        for review in sorted(
            reviews, key=lambda item: str(item.get("review_id", "")) if isinstance(item, dict) else ""
        ):
            if not isinstance(review, dict) or review.get("subject_sha256") != request.exact_content_sha256:
                _deny("governing_review_subject_mismatch", "governing review does not bind the exact artefact")
            if review.get("scientific_review") != "approved":
                _deny("governing_review_blocking", "every governing scientific review must be approved")
            review_id = review.get("review_id")
            reviewer_actor = review.get("reviewer_actor_id", review.get("actor_id"))
            evidence_refs = review.get("evidence_refs")
            if (
                not isinstance(review_id, str)
                or not isinstance(reviewer_actor, str)
                or not isinstance(evidence_refs, list)
                or len(evidence_refs) != 1
                or review_id not in authority_refs
                or any(reference not in authority_refs for reference in evidence_refs)
            ):
                _deny("governing_review_unbound", "accepted use authority omits governing review evidence")
            if rule.get("prohibit_producer_reviewer") is True and reviewer_actor == producer_actor:
                _deny("reviewer_not_independent", "artefact producer cannot supply its governing review")
            matched: list[GoverningEvidenceResolution] = []
            for reference_id in evidence_refs:
                if not isinstance(reference_id, str):
                    _deny("review_evidence_invalid", "governing review evidence identity is invalid")
                resolution = self.governing_evidence.resolve(
                    reference_id,
                    project_id=request.project_id,
                    evaluation_time=request.evaluation_time,
                )
                record = resolution.record
                if (
                    resolution.reference_id != reference_id
                    or len(resolution.canonical_sha256) != 64
                    or sha256_hex(canonical_bytes(record)) != resolution.canonical_sha256
                    or set(record) != _REVIEW_RECORD_FIELDS
                ):
                    _deny("review_evidence_invalid", "governing review evidence identity is invalid")
                if (
                    record.get("schema_id") != "ars://evidence/governing-scientific-review"
                    or record.get("schema_version") != "1.0.0"
                    or record.get("project_id") != request.project_id
                    or record.get("subject_sha256") != request.exact_content_sha256
                    or record.get("reviewer_actor_id") != reviewer_actor
                    or record.get("status") != "active"
                    or (rule.get("require_eligible") is True and record.get("eligible") is not True)
                    or (rule.get("prohibit_related_reviewer") is True and record.get("related") is not False)
                    or _INDEPENDENCE_ORDER.get(record.get("independence_grade"), -1)
                    < _INDEPENDENCE_ORDER[minimum_grade]
                ):
                    _deny("review_evidence_ineligible", "governing review does not satisfy accepted independence")
                matched.append(resolution)
            if len(matched) != 1 or matched[0].record.get("review_id") != review_id:
                _deny("review_evidence_missing", "governing review lacks matching independent evidence")
            resolution = matched[0]
            census_rows.append(
                {
                    "review_id": review_id,
                    "stream_version": review.get("stream_version"),
                    "event_id": review.get("event_id"),
                    "event_hash": review.get("event_hash"),
                    "recorded_at": review.get("recorded_at"),
                }
            )
            rows.append(
                {
                    "review_id": review_id,
                    "artefact_stream_id": request.artefact_id,
                    "artefact_stream_version": review.get("stream_version"),
                    "event_id": review.get("event_id"),
                    "event_hash": review.get("event_hash"),
                    "recorded_at": review.get("recorded_at"),
                    "evidence_reference_ids": list(evidence_refs),
                    "exact_record_sha256": resolution.canonical_sha256,
                    "project_id": request.project_id,
                    "exact_subject_sha256": request.exact_content_sha256,
                    "reviewer_actor_id": reviewer_actor,
                    "status": resolution.record.get("status"),
                    "eligible": resolution.record.get("eligible"),
                    "related": resolution.record.get("related"),
                    "independence_grade": resolution.record.get("independence_grade"),
                }
            )
        if len(rows) < minimum:
            _deny("governing_review_incomplete", "complete governing review set is not satisfied")
        try:
            store_identity = self.ledger.store_identity
            if store_identity is None:
                store_manifest = load_store_manifest_unbound(self.ledger.control_root)
                store_identity = str(store_manifest["store_identity"])
            raw_prefix_sha256 = self.ledger.raw_prefix_sha256(bound_position)
        except Exception as exc:  # noqa: BLE001 - missing snapshot identity denies use
            raise ArtefactUseDenied(
                "review_snapshot_unavailable", "governing review snapshot identity is unavailable"
            ) from exc
        census_sha256 = sha256_hex(canonical_bytes(census_rows))
        set_preimage = {
            "schema_id": "ars://policy/governing-review-set-digest",
            "schema_version": "1.0.0",
            "store_identity": store_identity,
            "ledger_position": bound_position,
            "raw_prefix_sha256": bound_raw_prefix_sha256,
            "scientific_review_event_census_sha256": census_sha256,
            "reviews": rows,
        }
        set_sha256 = sha256_hex(canonical_bytes(set_preimage))
        required_binding_refs = [
            *(f"governing-review-id:{row['review_id']}" for row in rows),
            *(f"governing-review-record-sha256:{row['exact_record_sha256']}" for row in rows),
            f"governing-review-set-sha256:{set_sha256}",
            f"store-identity:{store_identity}",
            f"ledger-position:{bound_position}",
            f"raw-prefix-sha256:{bound_raw_prefix_sha256}",
        ]
        if raw_prefix_sha256 != bound_raw_prefix_sha256:
            _deny("review_snapshot_changed", "governing review raw ledger prefix no longer matches authority")
        if any(reference not in authority_refs for reference in required_binding_refs):
            _deny("governing_review_unbound", "current use authority omits its deterministic review-set proof")
        return _GoverningReviewProof(
            review_ids=tuple(str(row["review_id"]) for row in rows),
            record_sha256s=tuple(str(row["exact_record_sha256"]) for row in rows),
            set_sha256=set_sha256,
        )

    @staticmethod
    def _validate_decision(
        request: ArtefactUseRequest,
        contract: AcceptedArtefactAuthorityContract,
        state: Mapping[str, object],
        stream: Mapping[str, object],
        governing_review_ids: tuple[str, ...],
        events: tuple[dict[str, Any], ...],
    ) -> _DecisionProof | None:
        if request.required_decision_kind is None:
            return None
        rule = contract.decision_rules.get(request.required_decision_kind)
        decisions = state.get("decisions")
        authority_refs = stream.get("authority_evidence_refs")
        owner_actor = state.get("authority_owner_actor_id")
        if not isinstance(rule, dict) or not isinstance(decisions, dict) or not isinstance(authority_refs, list):
            _deny("decision_missing", "current authority has no governing owner decision")
        required_scope = f"{request.required_decision_kind}:{request.scope_id}"
        root_id = state.get("authority_root_id")
        root_grant = (
            state.get("authority_grants", {}).get(root_id) if isinstance(state.get("authority_grants"), dict) else None
        )
        if (
            not isinstance(owner_actor, str)
            or not isinstance(root_id, str)
            or not isinstance(root_grant, dict)
            or root_grant.get("status") != "active"
        ):
            _deny("decision_owner_unavailable", "verified replay has no unique active authority owner")
        active_superseded = {
            superseded
            for candidate in decisions.values()
            if isinstance(candidate, dict) and candidate.get("status") == "resolved"
            for superseded in candidate.get("superseded_decision_ids", [])
        }
        matches: list[_DecisionProof] = []
        for decision_id, decision in decisions.items():
            if not isinstance(decision_id, str) or not isinstance(decision, dict):
                continue
            if (
                decision.get("status") == "resolved"
                and decision.get("decision_kind") == request.required_decision_kind
                and decision.get("selected_option") == rule.get("selected_option")
                and decision.get("effective_scope") == required_scope
                and decision.get("deciding_actor_id") == owner_actor
                and rule.get("required_permitted_command") in decision.get("permitted_commands", [])
                and set(governing_review_ids) == set(decision.get("considered_review_ids", []))
                and decision_id in authority_refs
                and decision_id not in active_superseded
                and _parse_utc(decision.get("effective_at"), "decision effective_at") <= request.evaluation_time
                and _parse_utc(decision.get("expires_at"), "decision expires_at") > request.evaluation_time
            ):
                decision_events = [
                    event
                    for event in events
                    if event.get("stream_id") == decision_id
                    and event.get("event_type") == "DecisionResolved"
                    and event.get("actor_id") == owner_actor
                    and event.get("payload") == {key: decision.get(key) for key in event.get("payload", {})}
                ]
                if len(decision_events) != 1:
                    _deny("decision_event_ambiguous", "governing owner decision event is missing or ambiguous")
                decision_event = decision_events[0]
                projection_sha256 = decision_semantic_sha256(decision)
                reviewed_subject_hashes = {
                    subject_hash
                    for review_id in decision.get("considered_review_ids", [])
                    for review in [state.get("streams", {}).get(review_id)]
                    if isinstance(review, dict)
                    for subject_id, subject_hash in zip(
                        review.get("request", {}).get("subject_ids", []),
                        review.get("request", {}).get("subject_hashes", []),
                        strict=False,
                    )
                    if subject_id == decision_id
                }
                if len(reviewed_subject_hashes) != 1:
                    _deny("decision_subject_ambiguous", "governing decision lacks one exact reviewed subject hash")
                decision_subject_sha256 = next(iter(reviewed_subject_hashes))
                activation_events = [
                    event for event in events if event.get("event_id") == root_grant.get("activation_event_id")
                ]
                if len(activation_events) != 1:
                    _deny("decision_owner_unavailable", "authority owner activation evidence is ambiguous")
                activation_event = activation_events[0]
                required_refs = {
                    f"decision-id:{decision_id}",
                    f"decision-event-id:{decision_event['event_id']}",
                    f"decision-event-hash:{decision_event['event_hash']}",
                    f"decision-subject-sha256:{decision_subject_sha256}",
                    f"decision-projection-sha256:{projection_sha256}",
                    f"decision-authority-grant-id:{decision_event['authority_grant_id']}",
                    f"owner-actor-id:{owner_actor}",
                    f"authority-root-id:{root_id}",
                    f"authority-root-grant-sha256:{root_grant['authority_grant_sha256']}",
                    f"authority-root-activation-event-id:{activation_event['event_id']}",
                    f"authority-root-activation-event-hash:{activation_event['event_hash']}",
                }
                if not required_refs.issubset(set(authority_refs)):
                    _deny("decision_unbound", "current use authority omits exact P-005 replay bindings")
                matches.append(
                    _DecisionProof(
                        decision_id=decision_id,
                        event_id=str(decision_event["event_id"]),
                        event_hash=str(decision_event["event_hash"]),
                        projection_sha256=projection_sha256,
                    )
                )
        if len(matches) != 1:
            _deny("decision_missing", "exactly one current Stephen-attributed decision is required")
        return matches[0]
