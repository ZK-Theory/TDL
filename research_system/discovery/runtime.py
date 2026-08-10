from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command, Receipt
from research_system.discovery.authority import prepare_authority_transition, replay_authority
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierMember,
    RegisteredRoot,
    prepare_dossier_admission,
)
from research_system.errors import ConflictError, IntegrityError
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.receipts import ReceiptStore


_ACCEPTED = {
    "accepted_commit": "09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6",
    "accepted_tree": "151e0f8b24ad76913640aa0f1de66cd177a44f8f",
    "catalogue_blob": "8d58818540e04859f929d4b04c71e4cfa0512554",
    "catalogue_bytes": 136229,
    "catalogue_sha256": "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80",
    "bootstrap_blob": "aac7242072c3ce62370dd74d9a27a29e1a33070d",
    "bootstrap_sha256": "ebb7529a3bbf8faea9101b1556b3b71e6e0b3b9dbe0df163591466903d569d38",
    "review_commit": "bd61f00d05191de1fd330e997d33ba74ac1b506c",
    "review_blob": "2e0deee51e526cc712c6b04a79695abaa4fb6442",
    "review_sha256": "beb96faa0b58d3ba5faf326b94bb7bc7e1d6649b00c577f2239e1083fe09eaf9",
    "owner_decision": "I accept the KAN 84 envelope, proceed.",
}
_ROW_IDS = tuple(
    [*(f"OR-{number:03d}" for number in range(1, 42)), *(f"OR-{number:03d}" for number in range(101, 141))]
)
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


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()  # noqa: S324


def _validate_hash_chain(events: tuple[dict[str, Any], ...]) -> None:
    last_position = 0
    last_hash = "0" * 64
    for event in events:
        if event.get("global_position") != last_position + 1 or event.get("previous_event_hash") != last_hash:
            raise IntegrityError("Discovery event chain mismatch")
        unsigned = dict(event)
        recorded = unsigned.pop("event_hash", None)
        if recorded != sha256_hex(canonical_bytes(unsigned)):
            raise IntegrityError("Discovery event hash mismatch")
        last_position = event["global_position"]
        last_hash = event["event_hash"]


def replay_discovery(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    ordered = tuple(deepcopy(tuple(events)))
    _validate_hash_chain(ordered)
    state: dict[str, Any] = {
        "catalogue": None,
        "candidates": {},
        "assays": {},
        "spikes": {},
        "decisions": {},
        "reviews": {},
        "dossiers": {},
        "portfolio_objects": {},
        "scopes": {},
        "authority_events": [],
        "authorities": {},
        "authority_streams": {},
    }
    for event in ordered:
        event_type = event.get("event_type")
        payload = event.get("payload")
        if isinstance(payload, dict) and "authority_event_type" in payload:
            authority_event = {
                "owner_row_id": payload["owner_row_id"],
                "authority_kind": payload["authority_kind"],
                "event_type": payload["authority_event_type"],
                "payload": deepcopy(payload["authority_payload"]),
            }
            state["authority_events"].append(authority_event)
            state["authority_streams"][event["stream_id"]] = payload["authority_kind"]
            state["authorities"] = replay_authority(state["authority_events"])
            continue
        if event.get("command_type") in {
            "RequestW11AuthorityReview",
            "RecordW11AuthorityReview",
            "ProposeW11AuthorityDecision",
        } or (event.get("command_type") == "ResolveDecision" and event["stream_id"] in state["authority_streams"]):
            kind = state["authority_streams"].get(event["stream_id"])
            current = state["authorities"].get(kind, {})
            if event_type == "ReviewRequested":
                shadow = {
                    "actor_id": event["actor_id"],
                    "reviewer_actor_id": payload["reviewer_capability"][0],
                    "review_id": payload["new_review_id"],
                    "subject_sha256": current.get("subject_sha256"),
                    "file_sha256": current.get("file_sha256"),
                }
            elif event_type == "ReviewVerdictRecorded":
                shadow = {
                    "actor_id": event["actor_id"],
                    "verdict": payload["verdict"],
                    "unchanged_subject_sha256": payload["unchanged_subject_sha256"],
                    "unchanged_file_sha256": current.get("file_sha256"),
                    "reconstruction_sha256": payload["context_manifest_sha256"],
                }
            elif event_type == "DecisionProposed":
                shadow = {
                    "actor_id": event["actor_id"],
                    "decision_id": payload["new_decision_id"],
                    "proposed_decision": payload["recommendation"],
                    "subject_sha256": current.get("subject_sha256"),
                    "file_sha256": current.get("file_sha256"),
                }
            else:
                shadow = {
                    "actor_id": event["actor_id"],
                    "decision_id": payload["decision_id"],
                    "decision": payload["selected_option"],
                    "transaction_id": payload["conditions"][0],
                }
            state["authority_events"].append(
                {
                    "owner_row_id": {
                        "ReviewRequested": "OR-112" if kind == "dossier_expected_set" else "OR-118",
                        "ReviewVerdictRecorded": "OR-113" if kind == "dossier_expected_set" else "OR-119",
                        "DecisionProposed": "OR-114" if kind == "dossier_expected_set" else "OR-120",
                        "DecisionResolved": "OR-115" if kind == "dossier_expected_set" else "OR-121",
                    }[event_type],
                    "authority_kind": kind,
                    "event_type": event_type,
                    "payload": shadow,
                }
            )
            state["authorities"] = replay_authority(state["authority_events"])
            continue
        if event_type == "W11CatalogueGenesisImported":
            if state["catalogue"] is not None:
                raise IntegrityError("W11 genesis appears more than once")
            state["catalogue"] = deepcopy(payload)
        elif event_type == "CandidateRegistered":
            if state["catalogue"] is None:
                raise IntegrityError("Candidate event predates W11 genesis")
            candidate_id = payload.get("candidate_id") if isinstance(payload, dict) else None
            if not isinstance(candidate_id, str) or candidate_id in state["candidates"]:
                raise IntegrityError("Candidate identity collision")
            state["candidates"][candidate_id] = {**deepcopy(payload), "status": "registered", "version": 1}
        elif event_type == "AssayRequested":
            assay_id = payload.get("assay_id")
            candidate_id = payload.get("candidate_id")
            if (
                not isinstance(assay_id, str)
                or assay_id in state["assays"]
                or state["candidates"].get(candidate_id, {}).get("status") != "registered"
            ):
                raise IntegrityError("invalid Assay request transition")
            state["assays"][assay_id] = {
                "assay_id": assay_id,
                "candidate_id": candidate_id,
                "candidate_revision": payload["candidate_revision"],
                "candidate_sha256": payload["candidate_sha256"],
                "assay_bar_acceptance_sha256": payload["assay_bar_acceptance_sha256"],
                "producer_relation_sha256": payload["producer_relation_sha256"],
                "status": "requested",
                "version": event["stream_version"],
            }
        elif event_type == "AssayEvidenceCollectionOpened":
            assay = state["assays"].get(payload.get("assay_id"))
            if not isinstance(assay, dict) or assay.get("status") != "requested":
                raise IntegrityError("invalid Assay evidence transition")
            assay.update(status="evidence_collecting", version=event["stream_version"])
        elif event_type == "CandidateAssayRequested":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "registered":
                raise IntegrityError("invalid Candidate Assay transition")
            candidate.update(status="assay_pending", assay_id=payload["assay_id"], version=event["stream_version"])
        elif event_type == "AssayScored":
            assay = state["assays"].get(payload.get("assay_id"))
            if (
                not isinstance(assay, dict)
                or assay.get("status") != "evidence_collecting"
                or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
            ):
                raise IntegrityError("invalid Assay score transition")
            assay.update(
                status="scored",
                scorecard_sha256=payload["scorecard_sha256"],
                version=event["stream_version"],
            )
        elif event_type == "CandidateAssayLinked":
            candidate = state["candidates"].get(payload.get("candidate_id"))
            if not isinstance(candidate, dict) or candidate.get("status") != "assay_pending":
                raise IntegrityError("invalid Candidate Assay score transition")
            candidate.update(
                status="assay_scored",
                scorecard_sha256=payload["scorecard_sha256"],
                version=event["stream_version"],
            )
        elif event_type == "ReviewRequested":
            review_id = payload.get("new_review_id")
            if not isinstance(review_id, str) or review_id in state["reviews"]:
                raise IntegrityError("invalid Discovery review request")
            state["reviews"][review_id] = {
                "review_id": review_id,
                "subject_sha256": payload["subject_hashes"][0],
                "status": "pending",
                "version": event["stream_version"],
            }
        elif event_type == "AssayOutcomeReviewRequested":
            assay = state["assays"].get(payload.get("assay_id"))
            if not isinstance(assay, dict) or assay.get("status") != "scored":
                raise IntegrityError("invalid Assay outcome review request")
            assay.update(review_id=payload["review_id"], review_pending=True, version=event["stream_version"])
        elif event_type == "ReviewVerdictRecorded":
            review = state["reviews"].get(payload.get("review_id"))
            if (
                not isinstance(review, dict)
                or review.get("status") != "pending"
                or review.get("subject_sha256") != payload.get("unchanged_subject_sha256")
                or payload.get("verdict") != "approve"
            ):
                raise IntegrityError("invalid Discovery review verdict")
            review.update(status="satisfied", verdict="approve", version=event["stream_version"])
        elif event_type == "AssayReviewed":
            assay = state["assays"].get(payload.get("assay_id"))
            review = state["reviews"].get(payload.get("review_id"))
            if (
                not isinstance(assay, dict)
                or not assay.get("review_pending")
                or not isinstance(review, dict)
                or review.get("status") != "satisfied"
                or assay.get("scorecard_sha256") != payload.get("subject_sha256")
            ):
                raise IntegrityError("invalid Assay reviewed transition")
            assay.update(status="reviewed", review_pending=False, version=event["stream_version"])
        elif event_type == "DecisionProposed":
            decision_id = payload.get("new_decision_id")
            if not isinstance(decision_id, str) or decision_id in state["decisions"]:
                raise IntegrityError("invalid Discovery decision proposal")
            state["decisions"][decision_id] = {
                "status": "proposed",
                "kind": payload.get("discovery_kind"),
                "version": event["stream_version"],
            }
        elif event_type == "DecisionResolved":
            decision = state["decisions"].get(payload.get("decision_id"))
            if not isinstance(decision, dict) or decision.get("status") != "proposed":
                raise IntegrityError("invalid Discovery decision resolution")
            decision.update(
                status="resolved", selected_option=payload.get("selected_option"), version=event["stream_version"]
            )
        elif event_type == "CandidatePromotionRequested":
            state["candidates"][payload["candidate_id"]].update(
                status="promotion_pending", decision_id=payload["decision_id"]
            )
        elif event_type == "CandidatePromotionApplied":
            state["candidates"][payload["candidate_id"]].update(status="spike_planning_authorized")
        elif event_type == "SpikePlanned":
            spike_id = payload["spike_id"]
            if spike_id in state["spikes"]:
                raise IntegrityError("Spike identity collision")
            state["spikes"][spike_id] = {**deepcopy(payload), "status": "planned", "version": event["stream_version"]}
        elif event_type == "SpikeApprovalRequested":
            state["spikes"][payload["spike_id"]].update(status="approval_pending")
        elif event_type == "CandidateSpikePlanLinked":
            state["candidates"][payload["candidate_id"]].update(
                status="spike_approval_pending", spike_id=payload["spike_id"]
            )
        elif event_type == "SpikeExecutionDecisionRequested":
            state["spikes"][payload["spike_id"]].update(decision_id=payload["decision_id"])
        elif event_type == "SpikeAuthorized":
            state["spikes"][payload["spike_id"]].update(status="authorized")
        elif event_type == "CandidateSpikeAuthorized":
            state["candidates"][payload["candidate_id"]].update(status="spike_authorized")
        elif event_type == "SpikeStarted":
            state["spikes"][payload["spike_id"]].update(status="running", attempt_id=payload["attempt_id"])
        elif event_type == "CandidateSpikeStarted":
            state["candidates"][payload["candidate_id"]].update(status="spike_running")
        elif event_type == "SpikeVerdictRecorded":
            state["spikes"][payload["spike_id"]].update(
                status="verdict_recorded", verdict=payload["verdict"], verdict_sha256=payload["verdict_sha256"]
            )
        elif event_type == "CandidateSpikeVerdictLinked":
            state["candidates"][payload["candidate_id"]].update(status="spike_verdict_recorded")
        elif event_type == "SpikeReviewRequested":
            state["spikes"][payload["spike_id"]].update(review_id=payload["review_id"], review_pending=True)
        elif event_type == "SpikeReviewed":
            spike = state["spikes"][payload["spike_id"]]
            review = state["reviews"].get(payload["review_id"])
            if not spike.get("review_pending") or review.get("status") != "satisfied":
                raise IntegrityError("invalid Spike reviewed transition")
            spike.update(status="reviewed", review_pending=False)
        elif event_type == "ResearchDossierAdmitted":
            dossier_id = payload.get("dossier_id")
            if not isinstance(dossier_id, str) or dossier_id in state["dossiers"]:
                raise IntegrityError("Research dossier identity collision")
            state["dossiers"][dossier_id] = {**deepcopy(payload), "status": "admitted"}
        elif event_type == "PortfolioObjectRegistered":
            member_key = payload.get("member_key")
            if not isinstance(member_key, str) or member_key in state["portfolio_objects"]:
                raise IntegrityError("Portfolio object identity collision")
            state["portfolio_objects"][member_key] = deepcopy(payload)
        elif event_type == "ScopeDefinitionRegistered":
            member_key = payload.get("member_key")
            if not isinstance(member_key, str) or member_key in state["scopes"]:
                raise IntegrityError("Scope identity collision")
            state["scopes"][member_key] = deepcopy(payload)
        else:
            raise IntegrityError(f"unsupported Discovery event: {event_type}")
    return state


class DiscoveryRuntime:
    """Public, provider-free W11 genesis and Discovery lifecycle seam."""

    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        schemas: SchemaRegistry,
        *,
        catalogue_path: Path,
        accepted_expected_set: AcceptedExpectedSet | None = None,
        registered_roots: dict[str, RegisteredRoot] | None = None,
        current_expected_set_revision: int | None = None,
    ) -> None:
        self.control_root = control_root
        self.ledger = ledger
        self.schemas = schemas
        self.catalogue_path = catalogue_path
        self.receipts = ReceiptStore(control_root)
        self.accepted_expected_set = accepted_expected_set
        self.registered_roots = registered_roots
        self.current_expected_set_revision = current_expected_set_revision

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        if set(envelope) != _COMMAND_FIELDS or not isinstance(envelope.get("payload"), dict):
            raise IntegrityError("invalid Discovery command envelope")
        command = Command(deepcopy(envelope))
        if envelope["command_type"] == "ImportAcceptedW11CatalogueGenesis" and command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        existing = self.receipts.load(command.command_id)
        if existing is not None:
            if existing.payload_hash != command.payload_hash:
                raise ConflictError("command receipt payload mismatch")
            return existing

        snapshot = self.ledger.snapshot()
        committed = next(
            (event for event in snapshot.events if event.get("command_id") == command.command_id),
            None,
        )
        if committed is not None:
            if committed.get("command_payload_hash") != command.payload_hash:
                raise ConflictError("committed command payload mismatch")
            transaction_events = tuple(
                event for event in snapshot.events if event.get("transaction_id") == committed["transaction_id"]
            )
            target_versions = [
                event["stream_version"]
                for event in transaction_events
                if event.get("stream_id") == command.target_stream_id
            ]
            receipt = Receipt(
                status="accepted",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=committed["transaction_id"],
                observed_stream_version=max(target_versions),
                reason_code=None,
            )
            return self.receipts.write(receipt)
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
            return self.receipts.write(receipt)

        projection = replay_discovery(snapshot.events)
        if envelope["command_type"] == "ImportAcceptedW11CatalogueGenesis":
            event_type, event_payload = self._prepare_genesis(command, projection)
        elif envelope["command_type"] == "RegisterCandidate":
            prepared = [
                (self._prepare_candidate(command, projection)[0], command.target_stream_id, command.envelope["payload"])
            ]
        elif envelope["command_type"] in {
            "RequestAssay",
            "RecordAssayScore",
            "RequestDiscoveryOutcomeReview",
            "ReviewDiscoveryOutcome",
        }:
            if envelope["payload"].get("row_id") in {"OR-003", "OR-004", "OR-006", "OR-034"}:
                prepared = self._prepare_assay(command, projection)
            else:
                prepared = self._prepare_spike(command, projection)
        elif envelope["command_type"] in {
            "ProposePromotionDecision",
            "RegisterSpikePlan",
            "ProposeSpikeExecutionDecision",
            "StartSpike",
            "RecordSpikeVerdict",
        } or (
            envelope["command_type"] == "ResolveDecision" and envelope["payload"].get("row_id") in {"OR-013", "OR-016"}
        ):
            prepared = self._prepare_spike(command, projection)
        elif envelope["command_type"] == "AdmitResearchDossier":
            prepared = self._prepare_dossier(command, projection)
        elif envelope["command_type"] in {
            "RegisterDossierExpectedSetContent",
            "RegisterPathRegistrationContent",
            "ObserveW11AuthorityFile",
            "RequestW11AuthorityReview",
            "RecordW11AuthorityReview",
            "ProposeW11AuthorityDecision",
        } or (
            envelope["command_type"] == "ResolveDecision" and envelope["payload"].get("row_id") in {"OR-115", "OR-121"}
        ):
            prepared = self._prepare_authority(command, projection)
        else:
            raise IntegrityError(f"unsupported Discovery command: {envelope['command_type']}")
        if envelope["command_type"] == "ImportAcceptedW11CatalogueGenesis":
            prepared = [(event_type, command.target_stream_id, event_payload)]
        elif envelope["command_type"] == "RegisterCandidate":
            prepared = [("CandidateRegistered", command.target_stream_id, command.envelope["payload"])]
        binding = self.schemas.resolve_identity("ars://core/command", "1.0.0")
        result = self.ledger.append(
            [
                {
                    "event_type": prepared_event_type,
                    "schema_id": (
                        {
                            "ReviewRequested": "ars://core/event/ReviewRequested",
                            "ReviewVerdictRecorded": "ars://core/event/ReviewVerdictRecorded",
                            "DecisionProposed": "ars://core/event/DecisionProposed",
                            "DecisionResolved": "ars://core/event/DecisionResolved",
                        }.get(prepared_event_type, "ars://core/event")
                        if "authority_event_type" not in prepared_payload
                        else "ars://core/event"
                    ),
                    "schema_version": "1.0.0",
                    "stream_id": prepared_stream_id,
                    "command_id": command.command_id,
                    "command_type": envelope["command_type"],
                    "command_schema_id": binding.schema_id,
                    "command_schema_version": binding.schema_version,
                    "command_schema_sha256": binding.raw_bytes_sha256,
                    "idempotency_key": command.idempotency_key,
                    "command_payload_hash": command.payload_hash,
                    "correlation_id": command.idempotency_key,
                    "causation_id": None,
                    "actor_id": command.actor_id,
                    "authority_grant_id": envelope["authority_grant_id"],
                    "occurred_at": None,
                    "payload": prepared_payload,
                }
                for prepared_event_type, prepared_stream_id, prepared_payload in prepared
            ],
            snapshot=snapshot,
        )
        receipt = Receipt(
            status="accepted",
            command_id=command.command_id,
            payload_hash=command.payload_hash,
            event_batch_id=result["event_batch_id"],
            observed_stream_version=result["resulting_stream_versions"][command.target_stream_id],
            reason_code=None,
        )
        return self.receipts.write(receipt)

    @staticmethod
    def _prepare_authority(
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
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
        transition_payload = {
            key: deepcopy(value) for key, value in payload.items() if key not in {"row_id", "authority_kind"}
        }
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

        def stable_id(prefix: str, suffix: int) -> str:
            return (
                f"{prefix}_019fed25-b33e-7740-b280-{(1100 if kind == 'dossier_expected_set' else 1200) + suffix:012d}"
            )

        def persisted_payload(event: dict[str, object]) -> dict[str, Any]:
            event_type = str(event["event_type"])
            shadow = event["payload"]
            if event_type == "ReviewRequested":
                return {
                    "review_type": "provenance",
                    "new_review_id": stable_id("rev", 0),
                    "subject_ids": [stable_id("obj", 3)],
                    "subject_hashes": [current["subject_sha256"]],
                    "governing_refs": [f"W11:{event['owner_row_id']}"],
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
                    "deadline": "2026-08-12T00:00:00Z",
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
                    "governing_evidence_refs": [current["file_sha256"]],
                    "affected_task_ids": [],
                    "affected_claim_ids": [],
                    "required_authority": "owner",
                    "expires_at": "2026-08-12T00:00:00Z",
                    "review_date": "2026-08-11T00:00:00Z",
                    "consequences": [f"the exact {kind} subject becomes admission authority"],
                }
            if event_type == "DecisionResolved":
                return {
                    "decision_id": shadow["decision_id"],
                    "selected_option": shadow["decision"],
                    "effective_scope": f"exact {kind} subject",
                    "effective_at": "2026-08-11T00:00:00Z",
                    "decision_revision": 1,
                    "deciding_actor_id": command.actor_id,
                    "decision_authority_grant_id": command.envelope["authority_grant_id"],
                    "governing_evidence_refs": [current["file_sha256"]],
                    "considered_review_ids": [current["review_id"]],
                    "permitted_commands": ["AdmitResearchDossier"],
                    "superseded_decision_ids": [],
                    "conditions": [shadow["transaction_id"]],
                    "revisit_triggers": ["authority subject changes"],
                }
            return {
                "owner_row_id": event["owner_row_id"],
                "authority_kind": event["authority_kind"],
                "authority_event_type": event["event_type"],
                "authority_payload": shadow,
            }

        return [
            (
                str(event["event_type"]),
                command.target_stream_id,
                persisted_payload(event),
            )
            for event in events
        ]

    def _prepare_dossier(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> list[tuple[str, str, dict[str, Any]]]:
        expected = self.accepted_expected_set
        roots = self.registered_roots
        current_revision = self.current_expected_set_revision
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
            root_values = accepted_paths["subject"].get("registered_roots")
            if isinstance(root_values, list):
                roots = {
                    value["root_id"]: RegisteredRoot(
                        root_id=value["root_id"],
                        path=Path(value["path"]),
                        registration_revision=value["registration_revision"],
                        registration_hash=value["registration_hash"],
                        authorized=value.get("authorized", True),
                    )
                    for value in root_values
                }
        if expected is None or roots is None or current_revision is None:
            raise IntegrityError("accepted dossier authority is not active")
        payload = command.envelope["payload"]
        if (
            set(payload) != {"row_id", "dossier_id", "expected_set_id", "candidate_members"}
            or payload.get("row_id") != "OR-028"
            or payload.get("dossier_id") != expected.dossier_id
            or payload.get("expected_set_id") != expected.expected_set_id
            or command.target_stream_id != expected.dossier_id
            or not isinstance(payload.get("candidate_members"), list)
        ):
            raise IntegrityError("invalid AdmitResearchDossier command")
        try:
            members = tuple(DossierMember(**member) for member in payload["candidate_members"])
        except (TypeError, ValueError) as exc:
            raise IntegrityError("invalid dossier candidate member") from exc
        prepared = prepare_dossier_admission(
            expected_set=expected,
            current_expected_set_revision=current_revision,
            candidate_members=members,
            registered_roots=roots,
            existing_identities=frozenset(
                {
                    *projection["dossiers"],
                    *projection["portfolio_objects"],
                    *projection["scopes"],
                }
            ),
        )
        result: list[tuple[str, str, dict[str, Any]]] = []
        for event in prepared.events:
            event_type = event["event_type"]
            event_payload = event["payload"]
            stream_id = (
                expected.dossier_id if event_type == "ResearchDossierAdmitted" else str(event_payload["provenance_id"])
            )
            result.append((event_type, stream_id, event_payload))
        return result

    @staticmethod
    def _prepare_spike(command: Command, projection: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
        p = command.envelope["payload"]
        row = p.get("row_id")
        candidate_id, spike_id, decision_id, review_id = (
            p.get(k) for k in ("candidate_id", "spike_id", "decision_id", "review_id")
        )
        candidate = projection["candidates"].get(candidate_id)
        spike = projection["spikes"].get(spike_id)
        decision = projection["decisions"].get(decision_id)
        ct = command.envelope["command_type"]

        def out(*events: tuple[str, str]) -> list[tuple[str, str, dict[str, Any]]]:
            return [(event, stream, deepcopy(p.get("w2_payload", p))) for event, stream in events]

        if (
            ct == "ProposePromotionDecision"
            and row == "OR-012"
            and candidate
            and candidate.get("status") == "assay_scored"
            and command.target_stream_id == decision_id
        ):
            return [
                ("DecisionProposed", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionRequested", candidate_id, deepcopy(p)),
            ]
        if (
            ct == "ResolveDecision"
            and row == "OR-013"
            and decision
            and decision.get("status") == "proposed"
            and candidate
            and candidate.get("status") == "promotion_pending"
            and candidate.get("decision_id") == decision_id
            and command.target_stream_id == decision_id
            and p.get("w2_payload", {}).get("selected_option") == "approve"
        ):
            return [
                ("DecisionResolved", decision_id, deepcopy(p["w2_payload"])),
                ("CandidatePromotionApplied", candidate_id, deepcopy(p)),
            ]
        if (
            ct == "RegisterSpikePlan"
            and row == "OR-014"
            and candidate
            and candidate.get("status") == "spike_planning_authorized"
            and spike is None
            and command.target_stream_id == spike_id
            and isinstance(p.get("plan_sha256"), str)
            and len(p["plan_sha256"]) == 64
        ):
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
            and command.target_stream_id == decision_id
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
            and candidate
            and candidate.get("status") == "spike_approval_pending"
            and command.target_stream_id == decision_id
            and p.get("w2_payload", {}).get("selected_option") == "approve"
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
            and candidate
            and candidate.get("status") == "spike_authorized"
            and command.target_stream_id == spike_id
            and isinstance(p.get("attempt_id"), str)
            and isinstance(p.get("lease_id"), str)
        ):
            return out(("SpikeStarted", spike_id), ("CandidateSpikeStarted", candidate_id))
        if (
            ct == "RecordSpikeVerdict"
            and row == "OR-018"
            and spike
            and spike.get("status") == "running"
            and candidate
            and candidate.get("status") == "spike_running"
            and command.target_stream_id == spike_id
            and p.get("verdict") in {"PASS", "FAIL"}
            and isinstance(p.get("verdict_sha256"), str)
            and len(p["verdict_sha256"]) == 64
        ):
            return out(("SpikeVerdictRecorded", spike_id), ("CandidateSpikeVerdictLinked", candidate_id))
        if (
            ct == "RequestDiscoveryOutcomeReview"
            and row == "OR-036"
            and spike
            and spike.get("status") == "verdict_recorded"
            and command.target_stream_id == review_id
            and projection["reviews"].get(review_id) is None
            and p.get("subject_sha256") == spike.get("verdict_sha256")
            and p.get("review_contract", {}).get("new_review_id") == review_id
            and p.get("review_contract", {}).get("subject_ids") == [spike_id]
            and p.get("review_contract", {}).get("subject_hashes") == [spike.get("verdict_sha256")]
        ):
            return [
                ("ReviewRequested", review_id, deepcopy(p["review_contract"])),
                ("SpikeReviewRequested", spike_id, deepcopy(p)),
            ]
        if (
            ct == "ReviewDiscoveryOutcome"
            and row == "OR-020"
            and spike
            and spike.get("review_pending")
            and projection["reviews"].get(review_id, {}).get("status") == "pending"
            and command.target_stream_id == review_id
            and p.get("subject_sha256") == spike.get("verdict_sha256")
            and p.get("review_verdict", {}).get("verdict") == "approve"
            and p.get("review_verdict", {}).get("unchanged_subject_sha256") == spike.get("verdict_sha256")
        ):
            return [
                ("ReviewVerdictRecorded", review_id, deepcopy(p["review_verdict"])),
                ("SpikeReviewed", spike_id, deepcopy(p)),
            ]
        raise IntegrityError(f"invalid Spike transition: {ct}/{row}")

    @staticmethod
    def _prepare_assay(command: Command, projection: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
        payload = command.envelope["payload"]
        candidate_id = payload.get("candidate_id")
        assay_id = payload.get("assay_id")
        review_id = payload.get("review_id")
        candidate = projection["candidates"].get(candidate_id)
        assay = projection["assays"].get(assay_id)
        review = projection["reviews"].get(review_id)
        command_type = command.envelope["command_type"]
        if command_type == "RequestAssay":
            if (
                payload.get("row_id") != "OR-003"
                or command.target_stream_id != assay_id
                or not isinstance(candidate, dict)
                or candidate.get("status") != "registered"
                or candidate.get("revision") != payload.get("candidate_revision")
                or candidate.get("content_sha256") != payload.get("candidate_sha256")
                or assay is not None
            ):
                raise IntegrityError("invalid RequestAssay transition")
            return [
                ("AssayRequested", assay_id, deepcopy(payload)),
                ("AssayEvidenceCollectionOpened", assay_id, deepcopy(payload)),
                ("CandidateAssayRequested", candidate_id, deepcopy(payload)),
            ]
        if command_type == "RecordAssayScore":
            if (
                payload.get("row_id") != "OR-004"
                or command.target_stream_id != assay_id
                or not isinstance(assay, dict)
                or assay.get("status") != "evidence_collecting"
                or assay.get("candidate_id") != candidate_id
                or assay.get("producer_relation_sha256") != payload.get("producer_relation_sha256")
                or not isinstance(candidate, dict)
                or candidate.get("status") != "assay_pending"
            ):
                raise IntegrityError("invalid RecordAssayScore transition")
            return [
                ("AssayScored", assay_id, deepcopy(payload)),
                ("CandidateAssayLinked", candidate_id, deepcopy(payload)),
            ]
        if command_type == "RequestDiscoveryOutcomeReview":
            review_contract = payload.get("review_contract")
            if (
                payload.get("row_id") != "OR-034"
                or command.target_stream_id != review_id
                or review is not None
                or not isinstance(assay, dict)
                or assay.get("status") != "scored"
                or assay.get("scorecard_sha256") != payload.get("subject_sha256")
                or not isinstance(review_contract, dict)
                or review_contract.get("new_review_id") != review_id
                or review_contract.get("subject_ids") != [assay_id]
                or review_contract.get("subject_hashes") != [payload.get("subject_sha256")]
            ):
                raise IntegrityError("invalid RequestDiscoveryOutcomeReview transition")
            return [
                ("ReviewRequested", review_id, deepcopy(review_contract)),
                ("AssayOutcomeReviewRequested", assay_id, deepcopy(payload)),
            ]
        if command_type == "ReviewDiscoveryOutcome":
            review_verdict = payload.get("review_verdict")
            if (
                payload.get("row_id") != "OR-006"
                or command.target_stream_id != review_id
                or payload.get("verdict") != "approve"
                or not isinstance(review_verdict, dict)
                or review_verdict.get("review_id") != review_id
                or review_verdict.get("verdict") != "approve"
                or review_verdict.get("unchanged_subject_sha256") != payload.get("subject_sha256")
                or not isinstance(review, dict)
                or review.get("status") != "pending"
                or review.get("subject_sha256") != payload.get("subject_sha256")
                or not isinstance(assay, dict)
                or not assay.get("review_pending")
                or assay.get("review_id") != review_id
            ):
                raise IntegrityError("invalid ReviewDiscoveryOutcome transition")
            return [
                ("ReviewVerdictRecorded", review_id, deepcopy(review_verdict)),
                ("AssayReviewed", assay_id, deepcopy(payload)),
            ]
        raise IntegrityError(f"unsupported Assay command: {command_type}")

    def _prepare_genesis(
        self,
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        if projection["catalogue"] is not None:
            raise IntegrityError("W11 genesis already exists")
        if command.target_stream_id != "w11_catalogue" or command.expected_stream_version != 0:
            raise IntegrityError("W11 genesis stream identity mismatch")
        if command.envelope["payload"] != _ACCEPTED:
            raise IntegrityError("catalogue identity mismatch")
        raw = self.catalogue_path.read_bytes()
        if (
            len(raw) != _ACCEPTED["catalogue_bytes"]
            or sha256_hex(raw) != _ACCEPTED["catalogue_sha256"]
            or _git_blob(raw) != _ACCEPTED["catalogue_blob"]
        ):
            raise IntegrityError("catalogue identity mismatch")
        repository_root = self.catalogue_path.resolve().parents[3]
        bootstrap = (
            repository_root / ".research-system" / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml"
        )
        bootstrap_raw = bootstrap.read_bytes()
        if (
            sha256_hex(bootstrap_raw) != _ACCEPTED["bootstrap_sha256"]
            or _git_blob(bootstrap_raw) != _ACCEPTED["bootstrap_blob"]
        ):
            raise IntegrityError("bootstrap identity mismatch")
        catalogue = json.loads(raw)
        row_ids = tuple(row.get("owner_row_id") for row in catalogue.get("owner_contract_rows", ()))
        if catalogue.get("owner_row_count") != 81 or row_ids != _ROW_IDS or len(set(row_ids)) != 81:
            raise IntegrityError("catalogue row set mismatch")
        return (
            "W11CatalogueGenesisImported",
            {
                "accepted_commit": _ACCEPTED["accepted_commit"],
                "accepted_tree": _ACCEPTED["accepted_tree"],
                "catalogue_blob": _ACCEPTED["catalogue_blob"],
                "catalogue_bytes": _ACCEPTED["catalogue_bytes"],
                "catalogue_sha256": _ACCEPTED["catalogue_sha256"],
                "bootstrap_blob": _ACCEPTED["bootstrap_blob"],
                "bootstrap_sha256": _ACCEPTED["bootstrap_sha256"],
                "review_commit": _ACCEPTED["review_commit"],
                "review_blob": _ACCEPTED["review_blob"],
                "review_sha256": _ACCEPTED["review_sha256"],
                "row_count": 81,
                "row_ids": list(_ROW_IDS),
            },
        )

    @staticmethod
    def _prepare_candidate(
        command: Command,
        projection: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
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
        if command.target_stream_id in projection["candidates"]:
            raise IntegrityError("Candidate identity collision")
        return "CandidateRegistered", deepcopy(payload)
