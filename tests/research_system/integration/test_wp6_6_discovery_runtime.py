from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from datetime import UTC, datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid

import pytest

from research_system.discovery import runtime as discovery_runtime_module
from research_system.discovery.runtime import DiscoveryLedgerReplayError, DiscoveryRuntime, replay_discovery
from research_system.discovery.runtime import _DISCOVERY_IDENTITY_COLLECTIONS, _discovery_identity_exists
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.command.reducers import replay_control_plane
from research_system.errors import ArsError, ConflictError, IdempotencyConflictError, IntegrityError
from research_system.ids import new_id
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    ACTORS,
    PROJECT_ID,
    activate_lifecycle_grant,
    control_plane,
    revoke_lifecycle_grant,
)
from tests.research_system.integration.test_wp6_1_c1_readiness_lease import (
    ATTEMPT_ID as C1_ATTEMPT_ID,
    LEASE_ID as C1_LEASE_ID,
    RESOURCE_GRANT_ID as C1_RESOURCE_GRANT_ID,
    C1_NOW,
    C1_TRUSTED_RUNTIME_AUTHORITY,
    _seed_running_attempt,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
TDA_RUNTIME_ROOT = Path(os.environ.get("TDL_REPOSITORY_ROOT", Path.home() / "TDL"))
TDA_VAULT_ROOT = Path(os.environ.get("TDA_VAULT_ROOT", TDA_RUNTIME_ROOT / "vault"))
CATALOGUE = REPO_ROOT / ".research-system" / "evals" / "expected" / "w11-portfolio-discovery-v1.json"
CATALOGUE_STREAM_ID = "obj_019fed25-b33e-7740-b280-000000000001"
ACTOR_ID = ACTORS["actor-a"]
GRANT_ID = "agr_019fed25-b33e-7740-b280-6f661aaeff58"
ASSAY_RUBRIC_PATH = ".research-system/contracts/wp6-6/assay-rubric-content-v1.json"
ASSAY_SCOPE_PATH = ".research-system/contracts/wp6-6/assay-evidence-scope-content-v1.json"
ASSAY_AUTHORITY_ACTORS = tuple(f"act_019fed25-b33e-7740-b280-{number:012d}" for number in range(201, 207))
_HARNESSES = {}


def _rehash_events(events: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    rehashed = tuple(deepcopy(events))
    previous_hash = "0" * 64
    for event in rehashed:
        event["previous_event_hash"] = previous_hash
        unsigned = dict(event)
        unsigned.pop("event_hash", None)
        event["event_hash"] = sha256_hex(canonical_bytes(unsigned))
        previous_hash = event["event_hash"]
    return rehashed


def _reindex_and_rehash_events(events: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    """Rebuild positions and transaction cardinalities for a semantic deletion attack."""

    reindexed = tuple(deepcopy(events))
    transaction_events: dict[object, list[dict[str, object]]] = {}
    for global_position, event in enumerate(reindexed, start=1):
        event["global_position"] = global_position
        transaction_events.setdefault(event.get("transaction_id"), []).append(event)
    for members in transaction_events.values():
        for transaction_index, event in enumerate(members, start=1):
            event["transaction_index"] = transaction_index
            event["transaction_count"] = len(members)
    return _rehash_events(reindexed)


def _runtime(tmp_path: Path) -> DiscoveryRuntime:
    harness = _HARNESSES.get(tmp_path)
    if harness is None:
        harness = control_plane(
            tmp_path,
            clock=lambda: C1_NOW,
            trusted_runtime_authority_provider=lambda: C1_TRUSTED_RUNTIME_AUTHORITY,
        )
        _HARNESSES[tmp_path] = harness
    root = tmp_path / "discovery"
    root.mkdir(exist_ok=True)

    class GovernedDiscoveryRuntime(DiscoveryRuntime):
        def submit(self, envelope):
            value = deepcopy(envelope)
            command_type = value["command_type"]
            subject_kind = {
                "ImportAcceptedW11CatalogueGenesis": "scope_definition",
                "IngestScoutObservationBatch": "scope_definition",
                "RegisterCandidate": "scope_definition",
                "RequestAssay": "scope_definition",
                "RecordAssayScore": "scope_definition",
                "RecordAssayPartial": "scope_definition",
                "CancelDiscoveryEvaluation": "scope_definition",
                "ProposeRevisitDecision": "decision",
                "RequestDiscoveryOutcomeReview": "review",
                "ReviewDiscoveryOutcome": "review",
                "ProposePromotionDecision": "decision",
                "RegisterSpikePlan": "scope_definition",
                "ProposeSpikeExecutionDecision": "decision",
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
            }[command_type]
            subject_id = value["target_stream_id"]
            if command_type in {
                "RequestAssay",
                "RecordAssayScore",
                "RecordAssayPartial",
                "CancelDiscoveryEvaluation",
                "RegisterSpikePlan",
                "StartSpike",
                "RecordSpikeVerdict",
            }:
                subject_id = value["payload"]["candidate_id"]
            raw = bytearray(hashlib.sha256(f"{command_type}:{subject_id}".encode()).digest()[:16])
            raw[6] = (raw[6] & 0x0F) | 0x70
            raw[8] = (raw[8] & 0x3F) | 0x80
            grant_id = f"agr_{uuid.UUID(bytes=bytes(raw))}"
            activate_lifecycle_grant(
                harness,
                subject_kind=subject_kind,
                subject_id=subject_id,
                actor_id=value["actor_id"],
                allowed_actor_classes=(("human",) if value["actor_id"] == ACTOR_ID else ("agent",)),
                command_types=(command_type,),
                grant_id=grant_id,
            )
            value["authority_grant_id"] = grant_id
            return super().submit(value)

    return GovernedDiscoveryRuntime(
        root,
        harness.ledger,
        harness.schemas,
        catalogue_path=CATALOGUE,
        authority_resolver=harness.authority_resolver,
        clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
        repository_root=REPO_ROOT,
        root_tokens={
            "$REPOSITORY_CONTRACT_ROOT": TDA_RUNTIME_ROOT / ".research-system/contracts/wp6-4",
            "$TDA_VAULT_ROOT": TDA_VAULT_ROOT,
        },
        operational_ledger=harness.ledger,
    )


def _genesis() -> dict[str, object]:
    return {
        "command_id": new_id("command"),
        "command_type": "ImportAcceptedW11CatalogueGenesis",
        "actor_id": ACTOR_ID,
        "authority_grant_id": GRANT_ID,
        "idempotency_key": "wp6.6:w11:09be63a9",
        "target_stream_id": CATALOGUE_STREAM_ID,
        "expected_stream_version": 0,
        "payload": {
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
        },
    }


def _command(
    command_type: str,
    target_stream_id: str,
    expected_stream_version: int,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "command_id": new_id("command"),
        "command_type": command_type,
        "actor_id": ACTOR_ID,
        "authority_grant_id": GRANT_ID,
        "idempotency_key": f"wp6.6:{command_type}:{target_stream_id}:{expected_stream_version}",
        "target_stream_id": target_stream_id,
        "expected_stream_version": expected_stream_version,
        "payload": payload,
    }


def _ingest_candidate(
    runtime: DiscoveryRuntime,
    candidate_id: str,
    *,
    observation_id: str,
    title: str,
    expected_stream_version: int = 0,
) -> str:
    batch = {
        "schema_id": "ars://portfolio/scout-observation-batch",
        "schema_version": "1.0.0",
        "source_query": f"exact:{observation_id}",
        "source_version": "1",
        "observed_at": "2026-08-01T00:00:00Z",
        "returned_identifiers": [observation_id],
        "normalized_dedup_keys": [observation_id.casefold()],
        "raw_source_refs": [{"ref_kind": "external", "locator": observation_id, "content_hash": "9" * 64}],
        "matching_facts": [title],
        "omissions_or_errors": [],
        "viability_judgment_absent": True,
    }
    batch_sha256 = sha256_hex(canonical_bytes(batch))
    candidate_sha256 = sha256_hex(canonical_bytes([{"observation_id": observation_id, "content_sha256": batch_sha256}]))
    runtime.submit(
        _command(
            "IngestScoutObservationBatch",
            observation_id,
            expected_stream_version,
            {
                "row_id": "OR-029",
                "observation_id": observation_id,
                "batch": batch,
                "batch_sha256": batch_sha256,
                "candidate_blueprints": [
                    {
                        "candidate_id": candidate_id,
                        "revision": 1,
                        "content_sha256": candidate_sha256,
                        "source_observation_refs": [observation_id],
                        "title": title,
                    }
                ],
            },
        )
    )
    return candidate_sha256


def test_scout_observation_rejects_candidate_identity_from_any_existing_aggregate(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.submit(_genesis())
    shared_id = "obj_019fed25-b33e-7740-b280-6f661aaeff98"
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid Scout Candidate blueprint"):
        _ingest_candidate(runtime, shared_id, observation_id=shared_id, title="Colliding Candidate")
    assert tuple(runtime.ledger.iter_events()) == before
    _exercise_identity_attacks(runtime, shared_id)


def test_global_identity_contract_names_every_discovery_namespace() -> None:
    identity = "obj_019fed25-b33e-7740-b280-6f661aaeff94"
    empty = {collection: {} for collection in _DISCOVERY_IDENTITY_COLLECTIONS}
    empty["catalogue"] = None
    assert not _discovery_identity_exists(empty, identity)
    for collection in _DISCOVERY_IDENTITY_COLLECTIONS:
        state = deepcopy(empty)
        state[collection][identity] = {"identity": identity}
        assert _discovery_identity_exists(state, identity), collection
    state = deepcopy(empty)
    state["catalogue"] = {"status": "active"}
    assert _discovery_identity_exists(state, CATALOGUE_STREAM_ID)


@pytest.mark.parametrize(
    ("command_type", "payload"),
    [
        ("RequestAssay", {"assay_id": "obj_019fed25-b33e-7740-b280-6f661aaeff93"}),
        ("RecordAssayScore", {"assay_id": "obj_019fed25-b33e-7740-b280-6f661aaeff93"}),
        ("RecordAssayPartial", {"assay_id": "obj_019fed25-b33e-7740-b280-6f661aaeff93"}),
        (
            "CancelDiscoveryEvaluation",
            {"evaluation_kind": "assay", "assay_id": "obj_019fed25-b33e-7740-b280-6f661aaeff93"},
        ),
        ("RegisterSpikePlan", {"spike_id": "obj_019fed25-b33e-7740-b280-6f661aaeff93"}),
        ("StartSpike", {"spike_id": "obj_019fed25-b33e-7740-b280-6f661aaeff93"}),
        ("RecordSpikeVerdict", {"spike_id": "obj_019fed25-b33e-7740-b280-6f661aaeff93"}),
    ],
)
def test_candidate_scoped_commands_cannot_write_a_foreign_stream(command_type: str, payload: dict[str, object]) -> None:
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff92"
    foreign_stream = "obj_019fed25-b33e-7740-b280-6f661aaeff93"
    projection = {
        "catalogue": {"status": "active"},
        **{collection: {} for collection in _DISCOVERY_IDENTITY_COLLECTIONS},
    }
    projection["candidates"] = {
        candidate_id: {"candidate_id": candidate_id},
        foreign_stream: {"candidate_id": foreign_stream},
    }
    envelope = _command(
        command_type,
        foreign_stream,
        1,
        {"candidate_id": candidate_id, **payload},
    )
    with pytest.raises(IntegrityError, match="outside authorized Candidate"):
        DiscoveryRuntime._require_candidate_target(Command(envelope), projection)


def _exercise_identity_attacks(runtime: DiscoveryRuntime, shared_id: str) -> None:
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff99"
    candidate_sha256 = _ingest_candidate(runtime, candidate_id, observation_id=shared_id, title="Distinct Candidate")
    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    foreign_candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff96"
    _ingest_candidate(
        runtime,
        foreign_candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff95",
        title="Foreign Candidate stream",
    )
    for occupied_stream in (CATALOGUE_STREAM_ID, foreign_candidate_id):
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="outside authorized Candidate"):
            runtime.submit(
                _command(
                    "RequestAssay",
                    occupied_stream,
                    1,
                    {
                        "row_id": "OR-003",
                        "candidate_id": candidate_id,
                        "assay_id": occupied_stream,
                        "candidate_revision": 1,
                        "candidate_sha256": candidate_sha256,
                        "assay_bar_acceptance_sha256": bar_sha256,
                        "producer_relation_sha256": producer_sha256,
                    },
                )
            )
        assert tuple(runtime.ledger.iter_events()) == before
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="Candidate identity collision"):
        runtime.submit(
            _command(
                "RegisterCandidate",
                shared_id,
                1,
                {
                    "candidate_id": shared_id,
                    "revision": 1,
                    "content_sha256": candidate_sha256,
                    "source_observation_refs": [shared_id],
                    "title": "Standalone colliding Candidate",
                },
            )
        )
    assert tuple(runtime.ledger.iter_events()) == before
    tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    candidate_event = next(event for event in tampered if event["event_type"] == "CandidateRegistered")
    candidate_event["stream_id"] = shared_id
    candidate_event["stream_version"] = 2
    candidate_event["payload"]["candidate_id"] = shared_id
    with pytest.raises(IntegrityError, match="Candidate identity collision"):
        replay_discovery(_rehash_events(tampered))

    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid Scout observation ingestion"):
        _ingest_candidate(
            runtime,
            "obj_019fed25-b33e-7740-b280-6f661aaeff97",
            observation_id=candidate_id,
            title="Observation colliding with existing Candidate",
            expected_stream_version=1,
        )
    assert tuple(runtime.ledger.iter_events()) == before


def _accept_assay_bar(runtime: DiscoveryRuntime) -> tuple[str, str]:
    rubric = json.loads((REPO_ROOT / ASSAY_RUBRIC_PATH).read_bytes())
    scope = json.loads((REPO_ROOT / ASSAY_SCOPE_PATH).read_bytes())
    rubric_observer, scope_observer, requester, reviewer, author, decision_proposer = ASSAY_AUTHORITY_ACTORS
    owner = ACTOR_ID
    review_id = "rev_019fed25-b33e-7740-b280-000000000105"
    decision_id = "dec_019fed25-b33e-7740-b280-000000000107"
    producer_ref = {"id": ACTOR_ID, "record_revision": 1, "content_hash": "3" * 64}
    steps = (
        (
            "RegisterAssayRubricContent",
            author,
            rubric["record_id"],
            0,
            {
                "row_id": "OR-101",
                "authority_kind": "assay_bar",
                "content": rubric,
                "authority_file_path": ASSAY_RUBRIC_PATH,
            },
        ),
        (
            "RegisterAssayEvidenceScopeContent",
            author,
            scope["record_id"],
            0,
            {
                "row_id": "OR-102",
                "authority_kind": "assay_bar",
                "content": scope,
                "authority_file_path": ASSAY_SCOPE_PATH,
            },
        ),
        (
            "ObserveW11AuthorityFile",
            rubric_observer,
            rubric["record_id"],
            1,
            {"row_id": "OR-103", "authority_kind": "assay_bar"},
        ),
        (
            "ObserveW11AuthorityFile",
            scope_observer,
            scope["record_id"],
            1,
            {"row_id": "OR-104", "authority_kind": "assay_bar"},
        ),
        (
            "RequestW11AuthorityReview",
            requester,
            review_id,
            0,
            {
                "row_id": "OR-105",
                "authority_kind": "assay_bar",
                "reviewer_actor_id": reviewer,
                "prospective_producer_ref": producer_ref,
            },
        ),
        (
            "RecordW11AuthorityReview",
            reviewer,
            review_id,
            1,
            {
                "row_id": "OR-106",
                "authority_kind": "assay_bar",
                "verdict": "approve",
                "unchanged_subject_sha256": None,
                "reconstruction_sha256": "5" * 64,
            },
        ),
        (
            "ProposeW11AuthorityDecision",
            decision_proposer,
            decision_id,
            0,
            {"row_id": "OR-107", "authority_kind": "assay_bar", "proposed_decision": "accept"},
        ),
        (
            "ResolveDecision",
            owner,
            decision_id,
            1,
            {
                "row_id": "OR-108",
                "authority_kind": "assay_bar",
                "decision_id": decision_id,
                "decision": "accept",
            },
        ),
    )
    for command_type, actor_id, stream_id, version, payload in steps:
        if payload["row_id"] == "OR-106":
            payload["unchanged_subject_sha256"] = replay_discovery(runtime.ledger.iter_events())["assay_bar_authority"][
                "subject_sha256"
            ]
        command = _command(command_type, stream_id, version, payload)
        command["actor_id"] = actor_id
        if payload["row_id"] == "OR-106":
            wrong_stream = deepcopy(command)
            wrong_stream["target_stream_id"] = "rev_019fed25-b33e-7740-b280-ffffffffffff"
            with pytest.raises(IntegrityError, match="invalid Assay-bar review verdict"):
                runtime._prepare_assay_bar_authority(
                    Command(wrong_stream), replay_discovery(runtime.ledger.iter_events())
                )
        if payload["row_id"] == "OR-108":
            wrong_stream = deepcopy(command)
            wrong_stream["target_stream_id"] = "dec_019fed25-b33e-7740-b280-ffffffffffff"
            with pytest.raises(IntegrityError, match="invalid Assay-bar owner resolution"):
                runtime._prepare_assay_bar_authority(
                    Command(wrong_stream), replay_discovery(runtime.ledger.iter_events())
                )
        assert runtime.submit(command).status == "accepted"
    bar = replay_discovery(runtime.ledger.iter_events())["assay_bar_authority"]
    assert bar["status"] == "accepted"
    return bar["acceptance_sha256"], bar["producer_relation_sha256"]


def _scorecard(
    runtime: DiscoveryRuntime,
    candidate_id: str,
    assay_id: str,
    candidate_sha256: str,
    relation_sha256: str,
) -> dict[str, object]:
    projection = replay_discovery(runtime.ledger.iter_events())
    bar = projection["assay_bar_authority"]
    acceptance = bar["acceptance"]
    rubric = bar["contents"]["rubric"]["content"]
    scope = bar["contents"]["scope"]["content"]
    assay = projection["assays"][assay_id]
    file_refs = [
        _ref(rubric["record_id"], rubric["record_revision"], bar["observations"]["rubric"]["file_sha256"]),
        _ref(scope["record_id"], scope["record_revision"], bar["observations"]["scope"]["file_sha256"]),
    ]
    producer_ref = acceptance["prospective_producer_ref"]
    evidence_row = scope["evidence_rows"][0]
    return {
        "schema_id": "ars://portfolio/assay-scorecard",
        "schema_version": "1.0.0",
        "candidate_ref": {"id": candidate_id, "record_revision": 1, "content_hash": candidate_sha256},
        "assay_id": assay_id,
        "assay_requested_event_ref": _ref(assay_id, assay["request_version"], assay["requested_event_hash"]),
        "assay_relation_hash": relation_sha256,
        "rubric_ref": acceptance["rubric_ref"],
        "scope_ref": acceptance["scope_ref"],
        "assay_bar_acceptance_ref": _ref(acceptance["decision_id"], 1, bar["acceptance_sha256"]),
        "file_observation_refs": file_refs,
        "producer_relation_ref": producer_ref,
        "axis_results": [
            {
                "axis_id": "identity",
                "axis_kind": "gate",
                "value": True,
                "rationale": "Exact fixture evidence closes the declared axis.",
                "evidence_refs": file_refs,
                "unmet_condition_codes": [],
                "validator_id": evidence_row["validator_id"],
                "validator_hash": evidence_row["validator_hash"],
            }
        ],
        "required_axis_set_hash": acceptance["required_axis_set_hash"],
        "observed_axis_set_hash": sha256_hex(canonical_bytes(["identity"])),
        "mechanical_recommendation": "PROMOTE",
        "rule_evaluation_ref": _ref(
            rubric["rule_evaluation_algorithm_id"],
            1,
            rubric["rule_evaluation_algorithm_hash"],
        ),
        "limitations": [],
        "prohibited_inferences": ["The scorecard does not itself authorize promotion."],
        "producer_actor_id": ACTOR_ID,
        "producer_profile_ref": producer_ref,
        "producer_context_ref": producer_ref,
        "review_requirements": ["independent-review"],
    }


def _ref(record_id: object, revision: object, content_hash: object) -> dict[str, object]:
    return {"id": record_id, "record_revision": revision, "content_hash": content_hash}


def _promotion_relation(
    runtime: DiscoveryRuntime,
    *,
    decision_id: str,
    candidate_id: str,
    aggregate_id: str,
    review_id: str,
    gate: str,
    recommendation: str = "PROMOTE",
) -> dict[str, object]:
    projection = replay_discovery(runtime.ledger.iter_events())
    candidate = projection["candidates"][candidate_id]
    aggregate = projection["assays" if gate == "assay_to_spike" else "spikes"][aggregate_id]
    review = projection["reviews"][review_id]
    evidence_hash = aggregate.get("scorecard_sha256", aggregate.get("verdict_sha256"))
    aggregate_ref = _ref(aggregate_id, aggregate["version"], evidence_hash)
    return {
        "schema_id": "ars://portfolio/relation/discovery-promotion",
        "schema_version": "1.0.0",
        "relation_kind": "discovery_promotion",
        "decision_id": decision_id,
        "candidate_ref": _ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
        "gate": gate,
        "aggregate_ref": aggregate_ref,
        "aggregate_relation_hash": aggregate.get("producer_relation_sha256", aggregate.get("plan_sha256")),
        "evidence_ref": aggregate_ref,
        "selected_option": recommendation,
        "next_candidate_state": {
            "PROMOTE": {
                "assay_to_spike": "spike_planning_authorized",
                "spike_to_preregistration": "preregistration_authorized",
            }[gate],
            "PARK": "parked",
            "KILL": "killed",
        }[recommendation],
        "rationale": "The exact reviewed evidence supports this governed recommendation.",
        "considered_evidence_refs": [
            _ref(review_id, review["version"], review["verdict_event_hash"]),
        ],
        "conditions": [],
        "effective_scope": f"{gate}:{candidate_id}",
        "revisit_triggers": ["new objective evidence"],
        "actor_id": ACTOR_ID,
    }


def _revisit_relation(
    runtime: DiscoveryRuntime,
    *,
    decision_id: str,
    candidate_id: str,
    aggregate_id: str,
    review_id: str,
    predicate_observation_id: str,
    recommendation: str = "RETRY",
) -> dict[str, object]:
    projection = replay_discovery(runtime.ledger.iter_events())
    candidate = projection["candidates"][candidate_id]
    collection = "assays" if aggregate_id.startswith("asy_") else "spikes"
    aggregate = projection[collection][aggregate_id]
    review = projection["reviews"][review_id]
    predicate = projection["source_observations"][predicate_observation_id]
    aggregate_hash = aggregate.get(
        "scorecard_sha256",
        aggregate.get("verdict_sha256", aggregate.get("outcome_sha256")),
    )
    return {
        "schema_id": "ars://portfolio/relation/discovery-revisit",
        "schema_version": "1.0.0",
        "relation_kind": "discovery_revisit",
        "decision_id": decision_id,
        "candidate_ref": _ref(candidate_id, candidate["revision"], candidate["content_sha256"]),
        "prior_aggregate_ref": _ref(aggregate_id, aggregate["version"], aggregate_hash),
        "prior_outcome_review_ref": _ref(review_id, review["version"], review["verdict_event_hash"]),
        "satisfied_revisit_predicate_ref": _ref(predicate_observation_id, 1, predicate["content_sha256"]),
        "selected_option": recommendation,
        "actor_id": ACTOR_ID,
    }


def test_exact_w11_genesis_is_one_time_replay_safe_and_tamper_atomic(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    command = _genesis()

    accepted = runtime.submit(command)
    duplicate = runtime.submit(deepcopy(command))

    assert accepted.status == "accepted"
    assert duplicate == accepted
    events = tuple(runtime.ledger.iter_events())
    assert len(events) == 1
    projection = replay_discovery(events)
    assert projection["catalogue"]["row_count"] == 81
    assert projection["catalogue"]["row_ids"] == [
        *[f"OR-{number:03d}" for number in range(1, 42)],
        *[f"OR-{number:03d}" for number in range(101, 141)],
    ]

    tampered = _genesis()
    tampered["payload"]["catalogue_sha256"] = "0" * 64  # type: ignore[index]
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="catalogue identity mismatch"):
        runtime.submit(tampered)
    assert tuple(runtime.ledger.iter_events()) == before


def test_idempotency_key_is_a_durable_scope_not_decorative(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.submit(_genesis())
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff45"
    observation_id = "obj_019fed25-b33e-7740-b280-6f661aaeff46"
    _ingest_candidate(runtime, candidate_id, observation_id=observation_id, title="Exact retry")
    before = tuple(runtime.ledger.iter_events())
    command_id = next(
        event["command_id"]
        for event in reversed(before)
        if event["event_type"] == "ScoutObservationIngested" and event["stream_id"] == observation_id
    )
    receipt_path = runtime.receipts.receipts_root / f"{command_id}.json"
    receipt_path.unlink()

    _ingest_candidate(runtime, candidate_id, observation_id=observation_id, title="Exact retry")
    assert tuple(runtime.ledger.iter_events()) == before
    assert receipt_path.is_file()

    with pytest.raises(IdempotencyConflictError, match="idempotency key conflicts"):
        _ingest_candidate(runtime, candidate_id, observation_id=observation_id, title="Substituted payload")
    assert tuple(runtime.ledger.iter_events()) == before


def test_submit_surfaces_persisted_replay_failure_as_operational_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    runtime.submit(_genesis())
    before = tuple(runtime.ledger.iter_events())

    def fail_replay(events):
        tuple(events)
        raise IntegrityError("injected persisted corruption")

    monkeypatch.setattr(discovery_runtime_module, "replay_discovery", fail_replay)
    with pytest.raises(DiscoveryLedgerReplayError, match="persisted Discovery ledger failed replay"):
        runtime.submit(
            _command(
                "RegisterCandidate",
                "obj_019fed25-b33e-7740-b280-6f661aaeff47",
                0,
                {
                    "candidate_id": "obj_019fed25-b33e-7740-b280-6f661aaeff47",
                    "revision": 1,
                    "content_sha256": "1" * 64,
                    "source_observation_refs": ["obj_019fed25-b33e-7740-b280-6f661aaeff48"],
                    "title": "Operational fault distinction",
                },
            )
        )
    assert tuple(runtime.ledger.iter_events()) == before


@pytest.mark.integration
def test_composite_writer_fence_blocks_cross_process_authority_revocation(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.submit(_genesis())
    harness = _HARNESSES[tmp_path]
    revocation_subject_id = "obj_019fed25-b33e-7740-b280-00000000c002"
    activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=revocation_subject_id,
        command_types=("RegisterCandidate",),
    )
    signal = tmp_path / "writer-acquired.signal"
    release = tmp_path / "writer-release.signal"
    script = """
import sys
import time
from pathlib import Path
from research_system.store.lock import CompositeWriterLock

roots = tuple(Path(value) for value in sys.argv[1:4])
signal = Path(sys.argv[4])
release = Path(sys.argv[5])
with CompositeWriterLock(roots, {"command_id": "cmd_019fed25-b33e-7740-b280-00000000c001"}):
    signal.write_text("acquired", encoding="utf-8")
    deadline = time.monotonic() + 15
    while not release.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("parent did not release composite writer fence")
        time.sleep(0.02)
"""
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            script,
            str(runtime.control_root),
            str(runtime.authority_resolver.control_root),
            str(runtime.operational_ledger.control_root),
            str(signal),
            str(release),
        ],
        cwd=REPO_ROOT,
    )
    try:
        deadline = time.monotonic() + 10
        while not signal.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert signal.is_file(), process.poll()
        before = tuple(harness.authority_ledger.iter_events())
        with pytest.raises(ConflictError, match="writer lock exists"):
            revoke_lifecycle_grant(harness, subject_id=revocation_subject_id)
        assert tuple(harness.authority_ledger.iter_events()) == before
    finally:
        release.write_text("release", encoding="utf-8")
        process.wait(timeout=20)
    assert process.returncode == 0


@pytest.mark.parametrize("missing", ["repository", "catalogue"])
def test_runtime_configuration_path_failures_are_integrity_errors(tmp_path: Path, missing: str) -> None:
    harness = control_plane(tmp_path)
    root = tmp_path / "discovery-path-error"
    root.mkdir()
    repository_root = tmp_path / "missing-repository" if missing == "repository" else REPO_ROOT
    catalogue_path = tmp_path / "missing-catalogue.json" if missing == "catalogue" else CATALOGUE
    expected_message = "repository root is unavailable" if missing == "repository" else "catalogue path is unavailable"
    with pytest.raises(IntegrityError, match=expected_message):
        DiscoveryRuntime(
            root,
            harness.ledger,
            harness.schemas,
            catalogue_path=catalogue_path,
            authority_resolver=harness.authority_resolver,
            clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
            repository_root=repository_root,
            root_tokens={},
            operational_ledger=harness.ledger,
        )


@pytest.mark.parametrize("unavailable", ["catalogue", "bootstrap"])
def test_genesis_read_failures_are_integrity_errors_and_atomic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unavailable: str
) -> None:
    runtime = _runtime(tmp_path)
    if unavailable == "catalogue":
        runtime.catalogue_path = tmp_path / "missing-catalogue.json"
    else:
        original_read_bytes = Path.read_bytes

        def fail_bootstrap(path: Path) -> bytes:
            if path.name == "w11-materialization-bootstrap-contract.yaml":
                raise PermissionError("injected bootstrap read failure")
            return original_read_bytes(path)

        monkeypatch.setattr(Path, "read_bytes", fail_bootstrap)

    with pytest.raises(IntegrityError, match=f"{unavailable} .*unavailable"):
        runtime.submit(_genesis())
    assert tuple(runtime.ledger.iter_events()) == ()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "payload must be an object"),
        ({"authority_event_type": "ReviewRequested"}, "requires authority_payload"),
    ],
)
def test_replay_rejects_malformed_payload_as_integrity_error(payload: object, message: str) -> None:
    event = {
        "event_type": "SpikePlanned",
        "command_type": "RegisterSpikePlan",
        "payload": payload,
        "global_position": 1,
        "previous_event_hash": "0" * 64,
    }
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    with pytest.raises(IntegrityError, match=message):
        replay_discovery((event,))


def test_replay_rejects_unsupported_authority_event_type_as_integrity_error() -> None:
    event = {
        "event_type": "CandidateRegistered",
        "command_type": "RequestW11AuthorityReview",
        "stream_id": "rev_019fed25-b33e-7740-b280-6f661aaeff90",
        "payload": {"governing_refs": ["authority-kind:dossier_expected_set"]},
        "global_position": 1,
        "previous_event_hash": "0" * 64,
    }
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    with pytest.raises(IntegrityError, match="unsupported W11 authority event type"):
        replay_discovery((event,))


@pytest.mark.parametrize(
    ("event_type", "missing_field"),
    [("AssayRequested", "candidate_revision"), ("CandidateAssayRequested", "assay_id")],
)
def test_replay_rejects_ledger_derived_missing_fields_as_integrity_error(
    tmp_path: Path, event_type: str, missing_field: str
) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff80"
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff81"
    runtime.submit(_genesis())
    candidate_sha256 = _ingest_candidate(
        runtime,
        candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff82",
        title="Malformed replay probe",
    )
    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    runtime.submit(
        _command(
            "RequestAssay",
            assay_id,
            0,
            {
                "row_id": "OR-003",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "candidate_revision": 1,
                "candidate_sha256": candidate_sha256,
                "assay_bar_acceptance_sha256": bar_sha256,
                "producer_relation_sha256": producer_sha256,
            },
        )
    )
    events = [deepcopy(event) for event in runtime.ledger.iter_events()]
    for event in events:
        if event["event_type"] == event_type:
            event["payload"].pop(missing_field)
        event["previous_event_hash"] = (
            events[event["global_position"] - 2]["event_hash"] if event["global_position"] > 1 else "0" * 64
        )
        unsigned = dict(event)
        unsigned.pop("event_hash", None)
        event["event_hash"] = sha256_hex(canonical_bytes(unsigned))

    with pytest.raises(IntegrityError, match=f"requires {missing_field}"):
        replay_discovery(events)


def test_genesis_rejects_wrong_actor_scope_and_expired_grant_without_mutation(tmp_path: Path) -> None:
    harness = control_plane(tmp_path)
    root = tmp_path / "governed-discovery"
    root.mkdir()
    runtime = DiscoveryRuntime(
        root,
        harness.ledger,
        harness.schemas,
        catalogue_path=CATALOGUE,
        authority_resolver=harness.authority_resolver,
        clock=lambda: datetime(2026, 8, 2, tzinfo=UTC),
        repository_root=REPO_ROOT,
        root_tokens={
            "$REPOSITORY_CONTRACT_ROOT": TDA_RUNTIME_ROOT / ".research-system/contracts/wp6-4",
            "$TDA_VAULT_ROOT": TDA_VAULT_ROOT,
        },
        operational_ledger=harness.ledger,
    )
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=CATALOGUE_STREAM_ID,
        command_types=("ImportAcceptedW11CatalogueGenesis",),
    )

    wrong_actor = _genesis()
    wrong_actor["authority_grant_id"] = grant_id
    wrong_actor["actor_id"] = ACTORS["actor-b"]
    with pytest.raises(ArsError, match="authority actor mismatch"):
        runtime.submit(wrong_actor)

    foreign_id = "obj_019fed25-b33e-7740-b280-000000000099"
    foreign_grant = activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=foreign_id,
        command_types=("ImportAcceptedW11CatalogueGenesis",),
    )
    wrong_scope = _genesis()
    wrong_scope["authority_grant_id"] = foreign_grant
    with pytest.raises(ArsError, match="authority subject scope mismatch"):
        runtime.submit(wrong_scope)

    expired_grant = activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=CATALOGUE_STREAM_ID,
        command_types=("ImportAcceptedW11CatalogueGenesis",),
        grant_id="agr_019fed25-b33e-7740-b280-000000000098",
        expires_at="2026-08-01T00:00:01Z",
    )
    expired = _genesis()
    expired["authority_grant_id"] = expired_grant
    with pytest.raises(ArsError, match="expired"):
        runtime.submit(expired)

    assert tuple(runtime.ledger.iter_events()) == ()
    assert tuple(runtime.receipts.receipts_root.glob("*.json")) == ()


def test_candidate_registration_runs_through_durable_public_seam(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff58"
    candidate = {
        "command_id": new_id("command"),
        "command_type": "RegisterCandidate",
        "actor_id": ACTOR_ID,
        "authority_grant_id": GRANT_ID,
        "idempotency_key": f"wp6.6:candidate:{candidate_id}:1",
        "target_stream_id": candidate_id,
        "expected_stream_version": 0,
        "payload": {
            "candidate_id": candidate_id,
            "revision": 1,
            "content_sha256": "1" * 64,
            "source_observation_refs": ["obj_019fed25-b33e-7740-b280-6f661aaeff57"],
            "title": "TDA-scale dossier candidate",
        },
    }

    with pytest.raises(IntegrityError, match="W11 genesis is required"):
        runtime.submit(candidate)
    assert tuple(runtime.ledger.iter_events()) == ()

    runtime.submit(_genesis())
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="source observation is not registered"):
        runtime.submit(candidate)
    assert tuple(runtime.ledger.iter_events()) == before

    candidate_sha256 = _ingest_candidate(
        runtime,
        "obj_019fed25-b33e-7740-b280-6f661aaeff56",
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff57",
        title="Observation bootstrap candidate",
    )
    fabricated = deepcopy(candidate)
    fabricated["payload"]["content_sha256"] = "f" * 64
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="content hash does not match resolved observations"):
        runtime.submit(fabricated)
    assert tuple(runtime.ledger.iter_events()) == before

    candidate["payload"]["content_sha256"] = candidate_sha256
    receipt = runtime.submit(candidate)
    duplicate = runtime.submit(deepcopy(candidate))

    assert receipt.status == "accepted"
    assert duplicate == receipt
    restarted = _runtime(tmp_path)
    projection = replay_discovery(restarted.ledger.iter_events())
    assert projection["candidates"][candidate_id] == {
        "candidate_id": candidate_id,
        "revision": 1,
        "content_sha256": candidate_sha256,
        "source_observation_multiset_hash": candidate_sha256,
        "status": "registered",
        "source_observation_refs": ["obj_019fed25-b33e-7740-b280-6f661aaeff57"],
        "title": "TDA-scale dossier candidate",
        "version": 1,
    }


def test_genesis_retry_repairs_receipt_after_committed_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    command = _genesis()
    original_write = ReceiptStore.write
    calls = 0

    def interrupt_once(store: ReceiptStore, receipt: object) -> object:
        nonlocal calls
        if store.receipts_root.parent != tmp_path / "discovery":
            return original_write(store, receipt)  # type: ignore[arg-type]
        calls += 1
        if calls == 1:
            raise OSError("injected receipt interruption")
        return original_write(store, receipt)  # type: ignore[arg-type]

    monkeypatch.setattr(ReceiptStore, "write", interrupt_once)
    with pytest.raises(OSError, match="receipt interruption"):
        runtime.submit(command)
    assert len(tuple(runtime.ledger.iter_events())) == 1

    repaired = _runtime(tmp_path).submit(command)
    assert repaired.status == "accepted"
    assert len(tuple(runtime.ledger.iter_events())) == 1


@pytest.mark.parametrize(
    ("verdict", "review_status", "assay_status", "terminal_events"),
    [
        ("approve", "satisfied", "reviewed", ("ReviewVerdictRecorded", "AssayReviewed")),
        ("changes_requested", "changes_requested", "scored", ("ReviewVerdictRecorded",)),
    ],
)
def test_assay_verdict_lifecycle_is_atomic_durable_and_replay_equivalent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    verdict: str,
    review_status: str,
    assay_status: str,
    terminal_events: tuple[str, ...],
) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff58"
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff59"
    review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff5a"
    reviewer_id = "act_019fed25-b33e-7740-b280-6f661aaeff5b"
    runtime.submit(_genesis())
    candidate_sha256 = _ingest_candidate(
        runtime,
        candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff5c",
        title="TDA-scale dossier candidate",
    )

    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    requested = runtime.submit(
        _command(
            "RequestAssay",
            assay_id,
            0,
            {
                "row_id": "OR-003",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "candidate_revision": 1,
                "candidate_sha256": candidate_sha256,
                "assay_bar_acceptance_sha256": bar_sha256,
                "producer_relation_sha256": producer_sha256,
            },
        )
    )
    scorecard = _scorecard(runtime, candidate_id, assay_id, candidate_sha256, producer_sha256)
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))
    invented_axis = deepcopy(scorecard)
    invented_axis["axis_results"][0]["axis_id"] = "invented"
    invented_axis["observed_axis_set_hash"] = sha256_hex(canonical_bytes(["invented"]))
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid RecordAssayScore transition"):
        runtime.submit(
            _command(
                "RecordAssayScore",
                assay_id,
                2,
                {
                    "row_id": "OR-004",
                    "candidate_id": candidate_id,
                    "assay_id": assay_id,
                    "scorecard_sha256": sha256_hex(canonical_bytes(invented_axis)),
                    "scorecard_artifact": invented_axis,
                    "producer_relation_sha256": producer_sha256,
                },
            )
        )
    assert tuple(runtime.ledger.iter_events()) == before
    scored = runtime.submit(
        _command(
            "RecordAssayScore",
            assay_id,
            2,
            {
                "row_id": "OR-004",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "scorecard_sha256": scorecard_sha256,
                "scorecard_artifact": scorecard,
                "producer_relation_sha256": producer_sha256,
            },
        )
    )
    rehashed_invented_axis = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    scored_event = next(event for event in rehashed_invented_axis if event["event_type"] == "AssayScored")
    scored_event["payload"]["scorecard_artifact"]["axis_results"][0]["axis_id"] = "invented"
    scored_event["payload"]["scorecard_artifact"]["observed_axis_set_hash"] = sha256_hex(canonical_bytes(["invented"]))
    substituted_scorecard_hash = sha256_hex(canonical_bytes(scored_event["payload"]["scorecard_artifact"]))
    for event in rehashed_invented_axis:
        if event["command_id"] == scored_event["command_id"]:
            event["payload"]["scorecard_sha256"] = substituted_scorecard_hash
    with pytest.raises(IntegrityError, match="invalid Assay score transition"):
        replay_discovery(_rehash_events(rehashed_invented_axis))

    scored_prefix = tuple(runtime.ledger.iter_events())
    assay_bar_command_types = {
        "RegisterAssayRubricContent",
        "RegisterAssayEvidenceScopeContent",
        "ObserveW11AuthorityFile",
        "RequestW11AuthorityReview",
        "RecordW11AuthorityReview",
        "ProposeW11AuthorityDecision",
        "ResolveDecision",
    }
    without_assay_bar = tuple(
        deepcopy(event) for event in scored_prefix if event.get("command_type") not in assay_bar_command_types
    )
    with pytest.raises(IntegrityError, match="invalid Assay request transition"):
        replay_discovery(_reindex_and_rehash_events(without_assay_bar))

    fabricated_acceptance = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    request_event = next(event for event in fabricated_acceptance if event["event_type"] == "AssayRequested")
    request_event["payload"]["assay_bar_acceptance_sha256"] = "0" * 64
    with pytest.raises(IntegrityError, match="invalid Assay request transition"):
        replay_discovery(_rehash_events(fabricated_acceptance))

    rogue_producer = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    rogue_actor_id = "act_019fed25-b33e-7740-b280-0000000c0ffe"
    rogue_scored = next(event for event in rogue_producer if event["event_type"] == "AssayScored")
    rogue_scored["actor_id"] = rogue_actor_id
    rogue_scored["payload"]["scorecard_artifact"]["producer_actor_id"] = rogue_actor_id
    rogue_scorecard_sha256 = sha256_hex(canonical_bytes(rogue_scored["payload"]["scorecard_artifact"]))
    for event in rogue_producer:
        if event["command_id"] == rogue_scored["command_id"]:
            event["payload"]["scorecard_sha256"] = rogue_scorecard_sha256
    with pytest.raises(IntegrityError, match="invalid Assay score transition"):
        replay_discovery(_rehash_events(rogue_producer))
    review_request_command = _command(
        "RequestDiscoveryOutcomeReview",
        review_id,
        0,
        {
            "row_id": "OR-034",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": review_id,
            "subject_sha256": scorecard_sha256,
            "review_contract": {
                "review_type": "provenance",
                "new_review_id": review_id,
                "subject_ids": [assay_id],
                "subject_hashes": [scorecard_sha256],
                "governing_refs": ["W11:OR-034"],
                "review_questions": ["Does the exact Assay evidence satisfy the accepted bar?"],
                "required_evidence_refs": ["scorecard:exact"],
                "required_lanes": ["provenance"],
                "reviewer_capability": ["assay-independent-review"],
                "required_independence_grade": "independent",
                "visibility_policy": "owner-visible",
                "allowed_verdicts": [
                    "approve",
                    "approve_with_conditions",
                    "changes_requested",
                    "reject",
                    "unable_to_verify",
                    "withdrawn",
                ],
                "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
                "deadline": "2026-08-11T20:00:00Z",
                "escalation_rule": "owner-ruling",
            },
        },
    )
    colliding_review = deepcopy(review_request_command)
    authority_review_id = "rev_019fed25-b33e-7740-b280-000000000105"
    colliding_review["target_stream_id"] = authority_review_id
    colliding_review["expected_stream_version"] = runtime.ledger.snapshot().stream_versions[authority_review_id]
    colliding_review["payload"]["review_id"] = authority_review_id
    colliding_review["payload"]["review_contract"]["new_review_id"] = authority_review_id
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid RequestDiscoveryOutcomeReview transition"):
        runtime.submit(colliding_review)
    assert tuple(runtime.ledger.iter_events()) == before
    original_event_binding = SchemaRegistry.event_binding
    spoofed_shadow = deepcopy(review_request_command)
    spoofed_shadow["payload"]["review_contract"]["authority_event_type"] = "ReviewRequested"
    with pytest.raises(IntegrityError, match="invalid Discovery authority shadow payload"):
        runtime.submit(spoofed_shadow)
    assert runtime.receipts.load(review_request_command["command_id"]) is None
    assert all(event["command_id"] != review_request_command["command_id"] for event in runtime.ledger.iter_events())

    def missing_exact_producer_binding(
        schemas: SchemaRegistry,
        event_type: str,
        producer_command_type: str | None = None,
    ):
        if (event_type, producer_command_type) == (
            "ReviewRequested",
            "RequestDiscoveryOutcomeReview",
        ):
            return None
        return original_event_binding(schemas, event_type, producer_command_type)

    with monkeypatch.context() as patch_context:
        patch_context.setattr(SchemaRegistry, "event_binding", missing_exact_producer_binding)
        with pytest.raises(
            IntegrityError,
            match=("inactive Discovery event producer binding: ReviewRequested/RequestDiscoveryOutcomeReview"),
        ):
            runtime.submit(review_request_command)
    assert runtime.receipts.load(review_request_command["command_id"]) is None
    assert all(event["command_id"] != review_request_command["command_id"] for event in runtime.ledger.iter_events())
    review_requested = runtime.submit(review_request_command)
    review_command = _command(
        "ReviewDiscoveryOutcome",
        review_id,
        1,
        {
            "row_id": "OR-006",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": review_id,
            "subject_sha256": scorecard_sha256,
            "verdict": verdict,
            "review_verdict": {
                "review_id": review_id,
                "verdict": verdict,
                "findings": [],
                "required_evidence_refs": ["scorecard:exact"],
                "limitations": [],
                "conditions": [],
                "reviewer_actor_id": reviewer_id,
                "reviewer_profile": "independent-assay-reviewer",
                "reviewer_session": "session-wp66-assay-review",
                "reviewer_model_metadata": "independent-test-reviewer",
                "context_manifest_id": "ctx_019fed25-b33e-7740-b280-6f661aaeff5c",
                "context_manifest_sha256": "5" * 64,
                "unchanged_subject_sha256": scorecard_sha256,
                "producing_attempt_id": "att_019fed25-b33e-7740-b280-6f661aaeff5d",
                "trace_visibility_evidence_refs": ["trace:assay-review"],
                "computed_independence_grade": "independent",
            },
        },
    )
    review_command["actor_id"] = reviewer_id
    insufficient_independence = deepcopy(review_command)
    insufficient_independence["payload"]["review_verdict"]["computed_independence_grade"] = "related"
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid ReviewDiscoveryOutcome transition"):
        runtime.submit(insufficient_independence)
    assert tuple(runtime.ledger.iter_events()) == before
    reviewed = runtime.submit(review_command)

    assert [requested.status, scored.status, review_requested.status, reviewed.status] == ["accepted"] * 4
    batches = tuple(runtime.ledger.iter_batches())
    assert [tuple(event["event_type"] for event in batch) for batch in batches[-4:]] == [
        ("AssayRequested", "AssayEvidenceCollectionOpened", "CandidateAssayRequested"),
        ("AssayScored", "CandidateAssayLinked"),
        ("ReviewRequested", "AssayOutcomeReviewRequested"),
        terminal_events,
    ]
    projection = replay_discovery(_runtime(tmp_path).ledger.iter_events())
    assert projection["assays"][assay_id]["status"] == assay_status
    assert projection["assays"][assay_id]["scorecard_sha256"] == scorecard_sha256
    assert projection["candidates"][candidate_id]["status"] == "assay_scored"
    assert projection["reviews"][review_id]["status"] == review_status
    tampered_grade = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    next(
        event
        for event in tampered_grade
        if event["event_type"] == "ReviewVerdictRecorded" and event["stream_id"] == review_id
    )["payload"]["computed_independence_grade"] = "related"
    with pytest.raises(IntegrityError, match="invalid Discovery review verdict"):
        replay_discovery(_rehash_events(tampered_grade))
    if verdict == "changes_requested":
        replacement_review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff5e"
        prior = projection["reviews"][review_id]
        delta_scope = ["scorecard:resolved-provenance-gap"]
        changed_refs = ["scorecard:replacement-evidence"]
        replacement_subject_sha256 = sha256_hex(
            canonical_bytes(
                {
                    "unchanged_base_sha256": scorecard_sha256,
                    "accepted_delta_scope": delta_scope,
                    "changed_evidence_refs": changed_refs,
                }
            )
        )
        original_contract = next(
            event["payload"]
            for event in runtime.ledger.iter_events()
            if event["event_type"] == "ReviewRequested" and event["stream_id"] == review_id
        )
        replacement_contract = deepcopy(original_contract)
        replacement_contract.update(
            new_review_id=replacement_review_id,
            subject_hashes=[replacement_subject_sha256],
            required_evidence_refs=[*original_contract["required_evidence_refs"], *changed_refs],
        )
        replacement_payload = {
            "row_id": "OR-034",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": replacement_review_id,
            "subject_sha256": replacement_subject_sha256,
            "review_contract": replacement_contract,
            "review_subject_supersession": {
                "prior_review_id": review_id,
                "prior_request_event_id": prior["request_event_id"],
                "prior_request_event_hash": prior["request_event_hash"],
                "prior_verdict_event_id": prior["verdict_event_id"],
                "prior_verdict_event_hash": prior["verdict_event_hash"],
                "prior_subject_sha256": scorecard_sha256,
                "new_subject_sha256": replacement_subject_sha256,
                "changed_evidence_refs": changed_refs,
                "reason": "address the exact requested provenance evidence gap",
                "proposed_reviewer_relation": "independent-assay-replacement-reviewer",
                "mode": "bounded_delta",
                "unchanged_base_sha256": scorecard_sha256,
                "accepted_delta_scope": delta_scope,
            },
        }
        missing_relation = deepcopy(replacement_payload)
        missing_relation.pop("review_subject_supersession")
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="invalid RequestDiscoveryOutcomeReview transition"):
            runtime.submit(_command("RequestDiscoveryOutcomeReview", replacement_review_id, 0, missing_relation))
        assert tuple(runtime.ledger.iter_events()) == before
        runtime.submit(_command("RequestDiscoveryOutcomeReview", replacement_review_id, 0, replacement_payload))
        superseded = replay_discovery(runtime.ledger.iter_events())
        assert superseded["reviews"][review_id]["status"] == "superseded"
        assert superseded["reviews"][replacement_review_id]["status"] == "pending"
        tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
        next(
            event
            for event in tampered
            if event["event_type"] == "AssayOutcomeReviewRequested"
            and event["payload"].get("review_id") == replacement_review_id
        )["payload"].pop("review_subject_supersession")
        with pytest.raises(IntegrityError, match="invalid Assay review supersession"):
            replay_discovery(_rehash_events(tampered))
    if verdict == "approve":
        for tampered_verdict in ("approve", "approve_with_conditions"):
            events = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
            verdict_event = next(
                event
                for event in events
                if event["event_type"] == "ReviewVerdictRecorded" and event["payload"].get("review_id") == review_id
            )
            verdict_event["actor_id"] = ACTOR_ID
            verdict_event["payload"]["reviewer_actor_id"] = ACTOR_ID
            verdict_event["payload"]["verdict"] = tampered_verdict
            verdict_event["payload"]["conditions"] = (
                [
                    {
                        "gate_disposition": "non_blocking",
                        "owner_actor_id": ACTOR_ID,
                        "policy_id": "policy:assay-review",
                        "evidence_refs": ["scorecard:exact"],
                    }
                ]
                if tampered_verdict == "approve_with_conditions"
                else []
            )
            with pytest.raises(IntegrityError, match="invalid Discovery review verdict"):
                replay_discovery(_rehash_events(events))


def test_request_assay_requires_the_current_accepted_bar_and_producer_relation(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff60"
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff61"
    runtime.submit(_genesis())
    candidate_sha256 = _ingest_candidate(
        runtime,
        candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff62",
        title="Assay authority candidate",
    )

    def request(bar_hash: str, producer_hash: str) -> dict[str, object]:
        return _command(
            "RequestAssay",
            assay_id,
            0,
            {
                "row_id": "OR-003",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "candidate_revision": 1,
                "candidate_sha256": candidate_sha256,
                "assay_bar_acceptance_sha256": bar_hash,
                "producer_relation_sha256": producer_hash,
            },
        )

    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid RequestAssay transition"):
        runtime.submit(request("2" * 64, "3" * 64))
    assert tuple(runtime.ledger.iter_events()) == before

    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid RequestAssay transition"):
        runtime.submit(request("f" * 64, producer_sha256))
    assert tuple(runtime.ledger.iter_events()) == before

    stale = _command(
        "RecordAssayBarStaleness",
        "dec_019fed25-b33e-7740-b280-000000000107",
        3,
        {
            "row_id": "OR-109",
            "authority_kind": "assay_bar",
            "acceptance_sha256": bar_sha256,
            "trigger_evidence_refs": ["evidence:rubric-superseded"],
        },
    )
    stale["actor_id"] = ASSAY_AUTHORITY_ACTORS[1]
    assert runtime.submit(stale).status == "accepted"
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid RequestAssay transition"):
        runtime.submit(request(bar_sha256, producer_sha256))
    assert tuple(runtime.ledger.iter_events()) == before

    rubric = json.loads((REPO_ROOT / ASSAY_RUBRIC_PATH).read_bytes())
    rubric.update(record_revision=2, supersedes_revision=1)
    rubric["content_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in rubric.items() if key != "content_hash"})
    )
    successor = _command(
        "RegisterAssayRubricContent",
        rubric["record_id"],
        2,
        {
            "row_id": "OR-101",
            "authority_kind": "assay_bar",
            "content": rubric,
            "authority_file_path": ASSAY_RUBRIC_PATH,
        },
    )
    successor["actor_id"] = ASSAY_AUTHORITY_ACTORS[4]
    assert runtime.submit(successor).status == "accepted"
    successor_state = replay_discovery(runtime.ledger.iter_events())["assay_bar_authority"]
    assert successor_state["status"] == "content_registered"
    assert successor_state["contents"]["rubric"]["content"]["record_revision"] == 2
    assert successor_state["history"][0]["status"] == "stale"


@pytest.mark.parametrize(
    ("command_type", "replacement_actor", "message"),
    [
        ("ObserveW11AuthorityFile", ASSAY_AUTHORITY_ACTORS[0], "actor_not_independent"),
        ("ProposeW11AuthorityDecision", ASSAY_AUTHORITY_ACTORS[2], "invalid_decision_proposal"),
    ],
)
def test_assay_authority_replay_rejects_accumulated_actor_reuse(
    tmp_path: Path,
    command_type: str,
    replacement_actor: str,
    message: str,
) -> None:
    runtime = _runtime(tmp_path)
    runtime.submit(_genesis())
    _accept_assay_bar(runtime)
    events = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    matching = [event for event in events if event.get("command_type") == command_type]
    target = matching[-1]
    target["actor_id"] = replacement_actor
    authority_payload = target["payload"].get("authority_payload")
    if isinstance(authority_payload, dict):
        authority_payload["actor_id"] = replacement_actor
    with pytest.raises(IntegrityError, match=message):
        replay_discovery(_rehash_events(events))


def test_assay_partial_review_revisit_and_retry_run_through_public_seam(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff80"
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff81"
    retry_assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff82"
    review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff83"
    revisit_id = "dec_019fed25-b33e-7740-b280-6f661aaeff84"
    reviewer_id = "act_019fed25-b33e-7740-b280-6f661aaeff85"
    predicate_observation_id = "obj_019fed25-b33e-7740-b280-6f661aaeff8b"
    runtime.submit(_genesis())
    candidate_sha256 = _ingest_candidate(
        runtime,
        candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff86",
        title="Partial Assay candidate",
    )
    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    runtime.submit(
        _command(
            "RequestAssay",
            assay_id,
            0,
            {
                "row_id": "OR-003",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "candidate_revision": 1,
                "candidate_sha256": candidate_sha256,
                "assay_bar_acceptance_sha256": bar_sha256,
                "producer_relation_sha256": producer_sha256,
            },
        )
    )
    bar = replay_discovery(runtime.ledger.iter_events())["assay_bar_authority"]
    partial_artifact = {
        "schema_id": "ars://portfolio/assay-partial",
        "schema_version": "1.0.0",
        "assay_id": assay_id,
        "candidate_ref": {"id": candidate_id, "record_revision": 1, "content_hash": candidate_sha256},
        "rubric_ref": deepcopy(bar["acceptance"]["rubric_ref"]),
        "scope_ref": deepcopy(bar["acceptance"]["scope_ref"]),
        "assay_bar_acceptance_ref": {
            "id": bar["acceptance"]["decision_id"],
            "record_revision": 1,
            "content_hash": bar_sha256,
        },
        "assay_relation_hash": producer_sha256,
        "completed_axes": ["candidate identity"],
        "completed_evidence": ["evidence:candidate-identity"],
        "unmet_axes": ["remaining assay axes"],
        "unmet_evidence": [],
        "reason_codes": ["incomplete_axis_closure"],
        "limitations": ["incomplete axis closure"],
        "revisit_requirements": ["complete the remaining assay axes"],
        "mechanical_recommendation": "PARK",
    }
    partial_sha256 = sha256_hex(canonical_bytes(partial_artifact))
    partial_command = _command(
        "RecordAssayPartial",
        assay_id,
        2,
        {
            "row_id": "OR-005",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "producer_relation_sha256": producer_sha256,
            "partial_sha256": partial_sha256,
            "partial_artifact": partial_artifact,
        },
    )
    foreign_partial = deepcopy(partial_command)
    foreign_partial["payload"]["partial_artifact"]["candidate_ref"]["id"] = "obj_019fed25-b33e-7740-b280-ffffffffffff"
    foreign_partial["payload"]["partial_sha256"] = sha256_hex(
        canonical_bytes(foreign_partial["payload"]["partial_artifact"])
    )
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid RecordAssayPartial transition"):
        runtime.submit(foreign_partial)
    assert tuple(runtime.ledger.iter_events()) == before
    runtime.submit(partial_command)
    replay_foreign_partial = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    for event in replay_foreign_partial:
        if event["command_id"] != partial_command["command_id"]:
            continue
        event["payload"]["partial_artifact"]["candidate_ref"]["id"] = "obj_019fed25-b33e-7740-b280-ffffffffffff"
        event["payload"]["partial_sha256"] = sha256_hex(canonical_bytes(event["payload"]["partial_artifact"]))
    with pytest.raises(IntegrityError, match="invalid Assay partial transition"):
        replay_discovery(_rehash_events(replay_foreign_partial))
    review_contract = {
        "review_type": "provenance",
        "new_review_id": review_id,
        "subject_ids": [assay_id],
        "subject_hashes": [partial_sha256],
        "governing_refs": ["W11:OR-035"],
        "review_questions": ["Is the exact partial Assay outcome supported?"],
        "required_evidence_refs": ["assay-partial:exact"],
        "required_lanes": ["provenance"],
        "reviewer_capability": ["assay-independent-review"],
        "required_independence_grade": "independent",
        "visibility_policy": "owner-visible",
        "allowed_verdicts": ["approve", "changes_requested", "reject"],
        "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
        "deadline": "2026-08-12T00:00:00Z",
        "escalation_rule": "owner-ruling",
    }
    runtime.submit(
        _command(
            "RequestDiscoveryOutcomeReview",
            review_id,
            0,
            {
                "row_id": "OR-035",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "review_id": review_id,
                "subject_sha256": partial_sha256,
                "review_contract": review_contract,
            },
        )
    )
    review_verdict = {
        "review_id": review_id,
        "verdict": "approve",
        "findings": [],
        "required_evidence_refs": ["assay-partial:exact"],
        "limitations": [],
        "conditions": [],
        "reviewer_actor_id": reviewer_id,
        "reviewer_profile": "independent-assay-reviewer",
        "reviewer_session": "session-partial-assay",
        "reviewer_model_metadata": "test",
        "context_manifest_id": "ctx_019fed25-b33e-7740-b280-6f661aaeff87",
        "context_manifest_sha256": "8" * 64,
        "unchanged_subject_sha256": partial_sha256,
        "producing_attempt_id": "att_019fed25-b33e-7740-b280-6f661aaeff88",
        "trace_visibility_evidence_refs": ["trace:partial-assay"],
        "computed_independence_grade": "independent",
    }
    review = _command(
        "ReviewDiscoveryOutcome",
        review_id,
        1,
        {
            "row_id": "OR-007",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": review_id,
            "subject_sha256": partial_sha256,
            "verdict": "approve",
            "review_verdict": review_verdict,
        },
    )
    review["actor_id"] = reviewer_id
    foreign_candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff89"
    _ingest_candidate(
        runtime,
        foreign_candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff8a",
        title="Foreign Partial Assay candidate",
    )
    foreign_candidate_review = deepcopy(review)
    foreign_candidate_review["payload"]["candidate_id"] = foreign_candidate_id
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid ReviewDiscoveryOutcome transition"):
        runtime.submit(foreign_candidate_review)
    assert tuple(runtime.ledger.iter_events()) == before
    runtime.submit(review)
    _ingest_candidate(
        runtime,
        "obj_019fed25-b33e-7740-b280-6f661aaeff8c",
        observation_id=predicate_observation_id,
        title="Objective Assay revisit evidence",
    )
    proposal = {
        "question": "Retry the exact partial Assay?",
        "recommendation": "RETRY",
        "new_decision_id": revisit_id,
        "decision_revision": 1,
        "decision_kind": "design_lock",
        "options": ["RETRY", "PARK", "KILL"],
        "governing_evidence_refs": [review_id],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "expires_at": "2026-08-12T00:00:00Z",
        "review_date": "2026-08-11T00:00:00Z",
        "consequences": ["authorize exact retry"],
    }
    proposal_command = _command(
        "ProposeRevisitDecision",
        revisit_id,
        0,
        {
            "row_id": "OR-009",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": review_id,
            "decision_id": revisit_id,
            "w2_payload": proposal,
            "revisit_relation": _revisit_relation(
                runtime,
                decision_id=revisit_id,
                candidate_id=candidate_id,
                aggregate_id=assay_id,
                review_id=review_id,
                predicate_observation_id=predicate_observation_id,
            ),
        },
    )
    for mutation in ("foreign_review", "empty_options", "unbound_review", "foreign_predicate"):
        invalid = deepcopy(proposal_command)
        if mutation == "foreign_review":
            invalid["payload"]["review_id"] = "rev_019fed25-b33e-7740-b280-ffffffffffff"
        elif mutation == "empty_options":
            invalid["payload"]["w2_payload"]["options"] = []
        elif mutation == "unbound_review":
            invalid["payload"]["w2_payload"]["governing_evidence_refs"] = []
        else:
            invalid["payload"]["revisit_relation"]["satisfied_revisit_predicate_ref"]["id"] = review_id
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="invalid Assay revisit proposal"):
            runtime.submit(invalid)
        assert tuple(runtime.ledger.iter_events()) == before
    parked_projection = replay_discovery(runtime.ledger.iter_events())
    parked_projection["assays"][assay_id]["status"] = "reviewed"
    parked_projection["candidates"][candidate_id]["status"] = "parked"
    predicate_position = parked_projection["source_observations"][predicate_observation_id]["global_position"]
    parked_projection["candidates"][candidate_id]["parked_at_global_position"] = predicate_position - 1
    assert [
        event_type for event_type, _, _ in runtime._prepare_assay(Command(proposal_command), parked_projection)
    ] == [
        "DecisionProposed",
        "AssayRevisitRequested",
        "CandidateAssayRevisitRequested",
    ]
    parked_projection["candidates"][candidate_id]["parked_at_global_position"] = predicate_position
    with pytest.raises(IntegrityError, match="invalid Assay revisit proposal"):
        runtime._prepare_assay(Command(proposal_command), parked_projection)
    runtime.submit(proposal_command)
    resolution = {
        "decision_id": revisit_id,
        "selected_option": "RETRY",
        "effective_scope": "exact partial Assay",
        "decision_revision": 1,
        "deciding_actor_id": ACTOR_ID,
        "decision_authority_grant_id": GRANT_ID,
        "governing_evidence_refs": [review_id],
        "considered_review_ids": [review_id],
        "effective_at": "2026-08-11T00:00:00Z",
        "permitted_commands": ["RequestAssay"],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    runtime.submit(
        _command(
            "ResolveDecision",
            revisit_id,
            1,
            {
                "row_id": "OR-010",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "decision_id": revisit_id,
                "w2_payload": resolution,
            },
        )
    )
    runtime.submit(
        _command(
            "RequestAssay",
            retry_assay_id,
            0,
            {
                "row_id": "OR-011",
                "candidate_id": candidate_id,
                "old_assay_id": assay_id,
                "assay_id": retry_assay_id,
                "candidate_revision": 1,
                "candidate_sha256": candidate_sha256,
                "assay_bar_acceptance_sha256": bar_sha256,
                "producer_relation_sha256": producer_sha256,
            },
        )
    )
    projection = replay_discovery(runtime.ledger.iter_events())
    assert projection["assays"][assay_id]["status"] == "superseded"
    assert projection["assays"][retry_assay_id]["status"] == "evidence_collecting"
    assert projection["candidates"][candidate_id]["status"] == "assay_pending"
    assert tuple(event["event_type"] for event in tuple(runtime.ledger.iter_batches())[-1]) == (
        "AssayRequested",
        "AssayEvidenceCollectionOpened",
        "AssaySuperseded",
        "CandidateAssayRetryStarted",
    )
    for event_type in ("AssayRevisitRequested", "AssayRevisitResolved"):
        tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
        next(event for event in tampered if event["event_type"] == event_type)["payload"]["candidate_id"] = (
            "obj_019fed25-b33e-7740-b280-ffffffffffff"
        )
        with pytest.raises(IntegrityError, match="invalid Discovery revisit"):
            replay_discovery(_rehash_events(tampered))
    tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    next(event for event in tampered if event["event_type"] == "AssayRevisitRequested")["payload"]["review_id"] = (
        "rev_019fed25-b33e-7740-b280-ffffffffffff"
    )
    with pytest.raises(IntegrityError, match="invalid Discovery revisit request"):
        replay_discovery(_rehash_events(tampered))
    tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    next(event for event in tampered if event["event_type"] == "AssayRevisitRequested")["payload"]["w2_payload"][
        "new_decision_id"
    ] = "dec_019fed25-b33e-7740-b280-ffffffffffff"
    with pytest.raises(IntegrityError, match="invalid Discovery revisit request"):
        replay_discovery(_rehash_events(tampered))
    tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    next(event for event in tampered if event["event_type"] == "AssayRevisitRequested")["payload"]["revisit_relation"][
        "satisfied_revisit_predicate_ref"
    ]["content_hash"] = "f" * 64
    with pytest.raises(IntegrityError, match="invalid Discovery revisit request"):
        replay_discovery(_rehash_events(tampered))
    cross_candidate_review = [deepcopy(event) for event in runtime.ledger.iter_events()]
    reviewed_index = next(
        index for index, event in enumerate(cross_candidate_review) if event["event_type"] == "AssayPartialReviewed"
    )
    cross_candidate_review = cross_candidate_review[: reviewed_index + 1]
    cross_candidate_review[-1]["payload"]["candidate_id"] = foreign_candidate_id
    with pytest.raises(IntegrityError, match="invalid Assay reviewed transition"):
        replay_discovery(_rehash_events(cross_candidate_review))
    excluded_option = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    next(
        event
        for event in excluded_option
        if event["event_type"] == "DecisionProposed" and event["stream_id"] == revisit_id
    )["payload"]["options"] = ["PARK", "KILL"]
    with pytest.raises(IntegrityError, match="invalid Discovery revisit request"):
        replay_discovery(_rehash_events(excluded_option))


@pytest.mark.parametrize(("spike_verdict", "verdict_row"), [("PASS", "OR-018"), ("PARTIAL", "OR-019")])
def test_spike_positive_lifecycle_reaches_reviewed_atomically_and_without_provider_execution(
    tmp_path: Path, spike_verdict: str, verdict_row: str
) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff68"
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff69"
    spike_id = "spk_019fed25-b33e-7740-b280-6f661aaeff6a"
    promotion_id = "dec_019fed25-b33e-7740-b280-6f661aaeff6b"
    execution_id = "dec_019fed25-b33e-7740-b280-6f661aaeff6c"
    review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff6d"
    assay_review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff70"
    reviewer_id = "act_019fed25-b33e-7740-b280-6f661aaeff71"
    predicate_observation_id = "obj_019fed25-b33e-7740-b280-6f661aaeff77"
    attempt_id = C1_ATTEMPT_ID
    lease_id = C1_LEASE_ID
    resource_grant_id = C1_RESOURCE_GRANT_ID
    _seed_running_attempt(_HARNESSES[tmp_path])
    operational_state = _HARNESSES[tmp_path].replay().stream_states
    attempt_sha256 = sha256_hex(canonical_bytes(operational_state[attempt_id]))
    resource_state = operational_state[resource_grant_id]
    runtime.submit(_genesis())
    candidate_sha256 = _ingest_candidate(
        runtime,
        candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff75",
        title="Spike candidate",
    )
    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    runtime.submit(
        _command(
            "RequestAssay",
            assay_id,
            0,
            {
                "row_id": "OR-003",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "candidate_revision": 1,
                "candidate_sha256": candidate_sha256,
                "assay_bar_acceptance_sha256": bar_sha256,
                "producer_relation_sha256": producer_sha256,
            },
        )
    )
    scorecard = _scorecard(runtime, candidate_id, assay_id, candidate_sha256, producer_sha256)
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))
    runtime.submit(
        _command(
            "RecordAssayScore",
            assay_id,
            2,
            {
                "row_id": "OR-004",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "scorecard_sha256": scorecard_sha256,
                "scorecard_artifact": scorecard,
                "producer_relation_sha256": producer_sha256,
            },
        )
    )
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid Spike transition"):
        runtime.submit(
            _command(
                "ProposePromotionDecision",
                promotion_id,
                0,
                {
                    "row_id": "OR-012",
                    "candidate_id": candidate_id,
                    "decision_id": promotion_id,
                    "w2_payload": {},
                },
            )
        )
    assert tuple(runtime.ledger.iter_events()) == before
    runtime.submit(
        _command(
            "RequestDiscoveryOutcomeReview",
            assay_review_id,
            0,
            {
                "row_id": "OR-034",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "review_id": assay_review_id,
                "subject_sha256": scorecard_sha256,
                "review_contract": {
                    "review_type": "provenance",
                    "new_review_id": assay_review_id,
                    "subject_ids": [assay_id],
                    "subject_hashes": [scorecard_sha256],
                    "governing_refs": ["W11:OR-034"],
                    "review_questions": ["Is the scorecard exact?"],
                    "required_evidence_refs": ["scorecard:exact"],
                    "required_lanes": ["provenance"],
                    "reviewer_capability": ["assay-independent-review"],
                    "required_independence_grade": "independent",
                    "visibility_policy": "owner-visible",
                    "allowed_verdicts": [
                        "approve",
                        "approve_with_conditions",
                        "changes_requested",
                        "reject",
                        "unable_to_verify",
                        "withdrawn",
                    ],
                    "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
                    "deadline": "2026-08-12T00:00:00Z",
                    "escalation_rule": "owner-ruling",
                },
            },
        )
    )
    assay_review = _command(
        "ReviewDiscoveryOutcome",
        assay_review_id,
        1,
        {
            "row_id": "OR-006",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": assay_review_id,
            "subject_sha256": scorecard_sha256,
            "verdict": "approve",
            "review_verdict": {
                "review_id": assay_review_id,
                "verdict": "approve",
                "findings": [],
                "required_evidence_refs": ["scorecard:exact"],
                "limitations": [],
                "conditions": [],
                "reviewer_actor_id": reviewer_id,
                "reviewer_profile": "independent-assay-reviewer",
                "reviewer_session": "session-spike-assay",
                "reviewer_model_metadata": "test",
                "context_manifest_id": "ctx_019fed25-b33e-7740-b280-6f661aaeff72",
                "context_manifest_sha256": "7" * 64,
                "unchanged_subject_sha256": scorecard_sha256,
                "producing_attempt_id": "att_019fed25-b33e-7740-b280-6f661aaeff73",
                "trace_visibility_evidence_refs": ["trace:assay"],
                "computed_independence_grade": "independent",
            },
        },
    )
    assay_review["actor_id"] = reviewer_id
    impersonated_review = deepcopy(assay_review)
    impersonated_review["payload"]["review_verdict"]["reviewer_actor_id"] = ACTOR_ID
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid ReviewDiscoveryOutcome transition"):
        runtime.submit(impersonated_review)
    assert tuple(runtime.ledger.iter_events()) == before
    runtime.submit(assay_review)
    foreign_candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff74"
    _ingest_candidate(
        runtime,
        foreign_candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff76",
        title="Foreign candidate",
    )

    def proposed(decision_id: str, kind: str) -> dict[str, object]:
        return {
            "question": kind,
            "recommendation": "approve",
            "new_decision_id": decision_id,
            "decision_revision": 1,
            "decision_kind": "design_lock",
            "options": ["approve", "reject"],
            "governing_evidence_refs": ["evidence:exact"],
            "affected_task_ids": [],
            "affected_claim_ids": [],
            "required_authority": "owner",
            "expires_at": "2026-08-12T00:00:00Z",
            "review_date": "2026-08-11T00:00:00Z",
            "consequences": ["authorize next Discovery transition"],
        }

    def resolved(decision_id: str) -> dict[str, object]:
        return {
            "decision_id": decision_id,
            "selected_option": "approve",
            "effective_scope": "exact Discovery subject",
            "decision_revision": 1,
            "deciding_actor_id": ACTOR_ID,
            "decision_authority_grant_id": GRANT_ID,
            "governing_evidence_refs": ["evidence:exact"],
            "considered_review_ids": [],
            "effective_at": "2026-08-11T00:00:00Z",
            "permitted_commands": ["RegisterSpikePlan"],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": [],
        }

    def promotion_proposed(decision_id: str, gate: str) -> dict[str, object]:
        value = proposed(decision_id, gate)
        value.update(
            recommendation="PROMOTE",
            decision_kind="design_lock",
            options=["PROMOTE", "PARK", "KILL"],
        )
        return value

    def promotion_resolved(decision_id: str) -> dict[str, object]:
        value = resolved(decision_id)
        value["selected_option"] = "PROMOTE"
        return value

    candidate_ref = {"id": candidate_id, "record_revision": 1, "content_hash": candidate_sha256}
    assay_ref = {"id": assay_id, "record_revision": 1, "content_hash": scorecard_sha256}
    plan_artifact = {
        "schema_id": "ars://portfolio/spike-plan",
        "schema_version": "1.0.0",
        "spike_id": spike_id,
        "candidate_ref": candidate_ref,
        "originating_assay_ref": assay_ref,
        "source_scorecard_refs": [assay_ref],
        "assay_promotion_decision_ref": {
            "id": promotion_id,
            "record_revision": 1,
            "content_hash": "9" * 64,
        },
        "required_approving_authority": "Stephen",
        "time_resource_box": {"time_limit_seconds": 60, "worker_limit": 1, "network_access": False},
        "question": "Does the bounded provider-free predicate hold?",
        "scope": "Provider-free lifecycle proof.",
        "inputs": ["fixture:exact"],
        "method_or_object": "No-provider validation",
        "baselines": [],
        "null_or_comparator": None,
        "success_predicates": ["closure holds"],
        "failure_predicates": ["closure fails"],
        "kill_conditions": ["identity mismatch"],
        "partial_rules": ["unable to evaluate is partial"],
        "planned_contracts": ["W11:OR-018"],
        "outputs": ["spike verdict"],
        "prohibited_work": ["provider execution"],
        "outcome_to_next_step": {"PASS": "review"},
    }
    plan_sha256 = sha256_hex(canonical_bytes(plan_artifact))
    plan_ref = _ref(spike_id, 1, plan_sha256)
    execution_authority_relation = {
        "schema_id": "ars://portfolio/relation/spike-execution-authority",
        "schema_version": "1.0.0",
        "relation_kind": "spike_execution_authority",
        "decision_id": execution_id,
        "spike_ref": plan_ref,
        "candidate_ref": candidate_ref,
        "plan_ref": plan_ref,
        "resource_ref": _ref(resource_grant_id, 1, sha256_hex(canonical_bytes(resource_state))),
        "route_ref": plan_ref,
        "assurance_ref": assay_ref,
        "selected_option": "AUTHORIZE",
        "actor_id": ACTOR_ID,
    }
    verdict_artifact = {
        "schema_id": "ars://portfolio/spike-verdict",
        "schema_version": "1.0.0",
        "spike_id": spike_id,
        "candidate_ref": candidate_ref,
        "originating_assay_ref": assay_ref,
        "spike_plan_ref": {"id": spike_id, "record_revision": 1, "content_hash": plan_sha256},
        "attempt_ref": {"id": attempt_id, "record_revision": 1, "content_hash": attempt_sha256},
        "verdict": spike_verdict,
        "success_predicates": [{"predicate": "closure holds", "status": "passed", "evidence_refs": [candidate_ref]}],
        "failure_predicates": [{"predicate": "closure fails", "status": "passed", "evidence_refs": [candidate_ref]}],
        "kill_conditions": [
            {
                "condition": "identity mismatch",
                "status": "not_triggered",
                "evidence_refs": [candidate_ref],
                "consequence": "stop",
            }
        ],
        "artefact_refs": [candidate_ref],
        "validation_refs": [candidate_ref],
        "completed_scope": "The evaluable declared scope completed.",
        "unmet_scope": "One predicate remains unevaluated." if spike_verdict == "PARTIAL" else "None.",
        "limitations": ["One predicate could not be evaluated."] if spike_verdict == "PARTIAL" else [],
        "mechanical_recommendation": "PARK" if spike_verdict == "PARTIAL" else "NONE",
        "prohibited_inferences": ["This verdict does not authorize dispatch."],
    }
    if spike_verdict == "PARTIAL":
        verdict_artifact["success_predicates"][0]["status"] = "unable_to_evaluate"
        verdict_artifact["kill_conditions"][0]["status"] = "triggered"
    verdict_sha256 = sha256_hex(canonical_bytes(verdict_artifact))

    commands = [
        _command(
            "ProposePromotionDecision",
            promotion_id,
            0,
            {
                "row_id": "OR-012",
                "candidate_id": candidate_id,
                "decision_id": promotion_id,
                "review_id": assay_review_id,
                "w2_payload": promotion_proposed(promotion_id, "assay_to_spike"),
                "promotion_relation": _promotion_relation(
                    runtime,
                    decision_id=promotion_id,
                    candidate_id=candidate_id,
                    aggregate_id=assay_id,
                    review_id=assay_review_id,
                    gate="assay_to_spike",
                ),
            },
        ),
        _command(
            "ResolveDecision",
            promotion_id,
            1,
            {
                "row_id": "OR-013",
                "candidate_id": candidate_id,
                "decision_id": promotion_id,
                "w2_payload": promotion_resolved(promotion_id),
            },
        ),
        _command(
            "RegisterSpikePlan",
            spike_id,
            0,
            {
                "row_id": "OR-014",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "plan_sha256": plan_sha256,
                "plan_artifact": plan_artifact,
            },
        ),
        _command(
            "ProposeSpikeExecutionDecision",
            execution_id,
            0,
            {
                "row_id": "OR-015",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "decision_id": execution_id,
                "w2_payload": proposed(execution_id, "spike_execution"),
                "execution_authority_relation": execution_authority_relation,
            },
        ),
        _command(
            "ResolveDecision",
            execution_id,
            1,
            {
                "row_id": "OR-016",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "decision_id": execution_id,
                "w2_payload": resolved(execution_id),
                "execution_authority_relation": execution_authority_relation,
            },
        ),
        _command(
            "StartSpike",
            spike_id,
            4,
            {
                "row_id": "OR-017",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "attempt_id": attempt_id,
                "attempt_sha256": attempt_sha256,
                "lease_id": lease_id,
                "resource_grant_id": resource_grant_id,
            },
        ),
        _command(
            "RecordSpikeVerdict",
            spike_id,
            5,
            {
                "row_id": verdict_row,
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "verdict": spike_verdict,
                "verdict_sha256": verdict_sha256,
                "verdict_artifact": verdict_artifact,
                "evidence_refs": ["evidence:provider-free"],
            },
        ),
    ]
    for command in commands:
        row_id = command["payload"]["row_id"]
        if row_id in {"OR-012", "OR-015"}:
            malformed = deepcopy(command)
            malformed["payload"].pop("w2_payload")
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(malformed)
            assert tuple(runtime.ledger.iter_events()) == before
            substituted_decision = deepcopy(command)
            substituted_decision["payload"]["w2_payload"]["new_decision_id"] = (
                "dec_019fed25-b33e-7740-b280-ffffffffffff"
            )
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(substituted_decision)
            assert tuple(runtime.ledger.iter_events()) == before
        if row_id == "OR-012":
            for mutation in ("missing_relation", "foreign_candidate", "generic_decision"):
                invalid_promotion = deepcopy(command)
                if mutation == "missing_relation":
                    invalid_promotion["payload"].pop("promotion_relation")
                elif mutation == "foreign_candidate":
                    invalid_promotion["payload"]["promotion_relation"]["candidate_ref"]["content_hash"] = "f" * 64
                else:
                    invalid_promotion["payload"]["w2_payload"]["decision_kind"] = "claim_promotion"
                before = tuple(runtime.ledger.iter_events())
                with pytest.raises(IntegrityError, match="invalid Spike transition"):
                    runtime.submit(invalid_promotion)
                assert tuple(runtime.ledger.iter_events()) == before
        if row_id == "OR-015":
            for invalid_payload in (
                {**deepcopy(command["payload"]["w2_payload"]), "options": []},
                {**deepcopy(command["payload"]["w2_payload"]), "recommendation": "defer"},
            ):
                malformed_options = deepcopy(command)
                malformed_options["payload"]["w2_payload"] = invalid_payload
                before = tuple(runtime.ledger.iter_events())
                with pytest.raises(IntegrityError, match="invalid Spike transition"):
                    runtime.submit(malformed_options)
                assert tuple(runtime.ledger.iter_events()) == before
            foreign_resource = deepcopy(command)
            foreign_resource["payload"]["execution_authority_relation"]["resource_ref"]["content_hash"] = "f" * 64
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(foreign_resource)
            assert tuple(runtime.ledger.iter_events()) == before
            reused_decision = _command(
                "ProposeSpikeExecutionDecision",
                promotion_id,
                2,
                {
                    **deepcopy(command["payload"]),
                    "decision_id": promotion_id,
                    "w2_payload": proposed(promotion_id, "spike_execution"),
                },
            )
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(reused_decision)
            assert tuple(runtime.ledger.iter_events()) == before
            substituted = deepcopy(command)
            substituted["payload"]["candidate_id"] = foreign_candidate_id
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(substituted)
            assert tuple(runtime.ledger.iter_events()) == before
        if row_id in {"OR-013", "OR-016"}:
            malformed = deepcopy(command)
            malformed["payload"]["w2_payload"] = []
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(malformed)
            assert tuple(runtime.ledger.iter_events()) == before
            substituted = deepcopy(command)
            substituted["payload"]["w2_payload"]["decision_id"] = "dec_019fed25-b33e-7740-b280-ffffffffffff"
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(substituted)
            assert tuple(runtime.ledger.iter_events()) == before
        if row_id == "OR-016":
            invalid_projection = replay_discovery(runtime.ledger.iter_events())
            invalid_projection["decisions"][execution_id]["options"] = ["reject"]
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime._prepare_spike(Command(command), invalid_projection)
            foreign_relation = deepcopy(command)
            foreign_relation["payload"]["execution_authority_relation"]["route_ref"]["content_hash"] = "f" * 64
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(foreign_relation)
            assert tuple(runtime.ledger.iter_events()) == before
        if row_id == "OR-013":
            legacy_approval = deepcopy(command)
            legacy_approval["payload"]["w2_payload"]["selected_option"] = "approve"
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(legacy_approval)
            assert tuple(runtime.ledger.iter_events()) == before
        if row_id == "OR-018" and spike_verdict == "PASS":
            unevaluated = deepcopy(command)
            unevaluated_artifact = unevaluated["payload"]["verdict_artifact"]
            unevaluated_artifact["success_predicates"][0]["status"] = "unable_to_evaluate"
            unevaluated["payload"]["verdict_sha256"] = sha256_hex(canonical_bytes(unevaluated_artifact))
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(unevaluated)
            assert tuple(runtime.ledger.iter_events()) == before
            unknown_failure = deepcopy(command)
            unknown_failure_artifact = unknown_failure["payload"]["verdict_artifact"]
            unknown_failure_artifact["failure_predicates"][0]["status"] = "unable_to_evaluate"
            unknown_failure["payload"]["verdict_sha256"] = sha256_hex(canonical_bytes(unknown_failure_artifact))
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(unknown_failure)
            assert tuple(runtime.ledger.iter_events()) == before
            incomplete_fail = deepcopy(command)
            incomplete_artifact = incomplete_fail["payload"]["verdict_artifact"]
            incomplete_artifact["verdict"] = "FAIL"
            incomplete_artifact["success_predicates"][0]["status"] = "unable_to_evaluate"
            incomplete_artifact["failure_predicates"][0]["status"] = "failed"
            incomplete_fail["payload"]["verdict"] = "FAIL"
            incomplete_fail["payload"]["verdict_sha256"] = sha256_hex(canonical_bytes(incomplete_artifact))
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(incomplete_fail)
            assert tuple(runtime.ledger.iter_events()) == before
        if row_id in {"OR-018", "OR-019"}:
            mismatched_row = deepcopy(command)
            mismatched_row["payload"]["row_id"] = "OR-019" if row_id == "OR-018" else "OR-018"
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(mismatched_row)
            assert tuple(runtime.ledger.iter_events()) == before
        if row_id == "OR-019":
            current_clock = runtime.clock
            runtime.clock = lambda: datetime(2026, 8, 1, 13, 1, tzinfo=UTC)
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike operational closure"):
                runtime.submit(command)
            assert tuple(runtime.ledger.iter_events()) == before
            runtime.clock = current_clock
        if row_id == "OR-017":
            reused_projection = replay_discovery(runtime.ledger.iter_events())
            reused_projection["spikes"]["spk_019fed25-b33e-7740-b280-ffffffffffff"] = {
                "status": "running",
                "attempt_id": command["payload"]["attempt_id"],
                "lease_id": command["payload"]["lease_id"],
            }
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime._prepare_spike(Command(command), reused_projection)
            invented_hash = deepcopy(command)
            invented_hash["payload"]["attempt_sha256"] = "f" * 64
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(invented_hash)
            assert tuple(runtime.ledger.iter_events()) == before
            foreign = deepcopy(command)
            foreign["payload"]["resource_grant_id"] = "rgr_019fed25-b33e-7740-b280-ffffffffffff"
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(foreign)
            assert tuple(runtime.ledger.iter_events()) == before
            canonical_ledger = runtime.operational_ledger
            empty_root = tmp_path / "empty-operational"
            empty_root.mkdir()
            runtime.operational_ledger = EventLedger(empty_root, PROJECT_ID, _HARNESSES[tmp_path].schemas)
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(command)
            assert tuple(runtime.ledger.iter_events()) == before
            runtime.operational_ledger = canonical_ledger
        assert runtime.submit(command).status == "accepted"
        if row_id == "OR-013":
            for selected_option, next_state in (("PARK", "parked"), ("KILL", "killed")):
                terminal = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
                resolution_event = next(
                    event
                    for event in terminal
                    if event["event_type"] == "DecisionResolved" and event["stream_id"] == promotion_id
                )
                application_event = next(
                    event
                    for event in terminal
                    if event["event_type"] == "CandidatePromotionApplied"
                    and event["payload"].get("decision_id") == promotion_id
                )
                resolution_event["payload"]["selected_option"] = selected_option
                application_event["payload"]["selected_option"] = selected_option
                application_event["payload"]["next_candidate_state"] = next_state
                terminal_projection = replay_discovery(_rehash_events(terminal))
                assert terminal_projection["candidates"][candidate_id]["status"] == next_state
    invented_evidence = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    verdict_events = [
        event
        for event in invented_evidence
        if event.get("command_type") == "RecordSpikeVerdict"
        and isinstance(event.get("payload", {}).get("verdict_artifact"), dict)
    ]
    foreign_ref = _ref("obj_019fed25-b33e-7740-b280-ffffffffffff", 1, "f" * 64)
    for event in verdict_events:
        artifact = event["payload"]["verdict_artifact"]
        artifact["artefact_refs"] = [foreign_ref]
        artifact["validation_refs"] = [foreign_ref]
        for result in [
            *artifact["success_predicates"],
            *artifact["failure_predicates"],
            *artifact["kill_conditions"],
        ]:
            result["evidence_refs"] = [foreign_ref]
        event["payload"]["verdict_sha256"] = sha256_hex(canonical_bytes(artifact))
    with pytest.raises(IntegrityError, match="invalid Spike (partial )?verdict"):
        replay_discovery(_rehash_events(invented_evidence))
    invalid_promotion_relation = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    promotion_request = next(
        event
        for event in invalid_promotion_relation
        if event["event_type"] == "CandidatePromotionRequested"
        and event["payload"].get("promotion_gate") == "assay_to_spike"
    )
    promotion_request["payload"]["promotion_relation"]["candidate_ref"]["content_hash"] = "f" * 64
    with pytest.raises(IntegrityError, match="invalid Candidate promotion request"):
        replay_discovery(_rehash_events(invalid_promotion_relation))
    invalid_execution_relation = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    next(
        event
        for event in invalid_execution_relation
        if event["event_type"] == "SpikeExecutionDecisionRequested" and event["stream_id"] == spike_id
    )["payload"]["execution_authority_relation"]["route_ref"]["content_hash"] = "f" * 64
    with pytest.raises(IntegrityError, match="invalid Spike execution decision request"):
        replay_discovery(_rehash_events(invalid_execution_relation))
    substituted_resource_identity = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    for event in substituted_resource_identity:
        relation = event.get("payload", {}).get("execution_authority_relation")
        if isinstance(relation, dict):
            relation["resource_ref"]["content_hash"] = "f" * 64
    with pytest.raises(IntegrityError, match="invalid Spike execution decision request"):
        replay_discovery(_rehash_events(substituted_resource_identity))
    invalid_execution_options = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    proposal_event = next(
        event
        for event in invalid_execution_options
        if event["event_type"] == "DecisionProposed" and event["stream_id"] == execution_id
    )
    request_event = next(
        event for event in invalid_execution_options if event["event_type"] == "SpikeExecutionDecisionRequested"
    )
    for payload in (proposal_event["payload"], request_event["payload"]["w2_payload"]):
        payload["options"] = ["reject"]
        payload["recommendation"] = "reject"
    with pytest.raises(IntegrityError, match="invalid Spike execution decision request"):
        replay_discovery(_rehash_events(invalid_execution_options))
    if spike_verdict == "PARTIAL":
        operational = replay_control_plane(runtime._operational_events())
        assert operational.stream_states[attempt_id]["status"] == "partial"
        assert operational.stream_states[lease_id]["status"] == "released"
        partial_batch = tuple(
            event for event in runtime.ledger.iter_events() if event["command_id"] == commands[-1]["command_id"]
        )
        assert {event["event_type"] for event in partial_batch} == {
            "SpikePartialRecorded",
            "PartialOutcomeRecorded",
            "LeaseReleased",
            "SpikeAttemptClosed",
            "SpikeLeaseReleased",
            "CandidateSpikePartialLinked",
        }
        assert len({event["transaction_id"] for event in partial_batch}) == 1
    review_contract = {
        "review_type": "provenance",
        "new_review_id": review_id,
        "subject_ids": [spike_id],
        "subject_hashes": [verdict_sha256],
        "governing_refs": ["W11:OR-037" if spike_verdict == "PARTIAL" else "W11:OR-036"],
        "review_questions": ["Is the exact Spike verdict supported?"],
        "required_evidence_refs": ["evidence:provider-free"],
        "required_lanes": ["provenance"],
        "reviewer_capability": ["spike-independent-review"],
        "required_independence_grade": "independent",
        "visibility_policy": "owner-visible",
        "allowed_verdicts": [
            "approve",
            "approve_with_conditions",
            "changes_requested",
            "reject",
            "unable_to_verify",
            "withdrawn",
        ],
        "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
        "deadline": "2026-08-12T00:00:00Z",
        "escalation_rule": "owner-ruling",
    }
    runtime.submit(
        _command(
            "RequestDiscoveryOutcomeReview",
            review_id,
            0,
            {
                "row_id": "OR-037" if spike_verdict == "PARTIAL" else "OR-036",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "review_id": review_id,
                "subject_sha256": verdict_sha256,
                "review_contract": review_contract,
            },
        )
    )
    verdict = {
        "review_id": review_id,
        "verdict": "approve",
        "findings": [],
        "required_evidence_refs": ["evidence:provider-free"],
        "limitations": [],
        "conditions": [],
        "reviewer_actor_id": reviewer_id,
        "reviewer_profile": "independent-spike-reviewer",
        "reviewer_session": "session-spike",
        "reviewer_model_metadata": "test",
        "context_manifest_id": "ctx_019fed25-b33e-7740-b280-6f661aaeff6f",
        "context_manifest_sha256": "7" * 64,
        "unchanged_subject_sha256": verdict_sha256,
        "producing_attempt_id": attempt_id,
        "trace_visibility_evidence_refs": ["trace:spike"],
        "computed_independence_grade": "independent",
    }
    spike_review = _command(
        "ReviewDiscoveryOutcome",
        review_id,
        1,
        {
            "row_id": "OR-021" if spike_verdict == "PARTIAL" else "OR-020",
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "review_id": review_id,
            "subject_sha256": verdict_sha256,
            "review_verdict": verdict,
        },
    )
    spike_review["actor_id"] = reviewer_id
    mismatched_review = deepcopy(spike_review)
    mismatched_review["payload"]["review_verdict"]["review_id"] = assay_review_id
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="invalid Spike transition"):
        runtime.submit(mismatched_review)
    assert tuple(runtime.ledger.iter_events()) == before
    insufficient_independence = deepcopy(spike_review)
    insufficient_independence["payload"]["review_verdict"]["computed_independence_grade"] = "related"
    with pytest.raises(IntegrityError, match="invalid Spike transition"):
        runtime.submit(insufficient_independence)
    assert tuple(runtime.ledger.iter_events()) == before
    runtime.submit(spike_review)

    projection = replay_discovery(_runtime(tmp_path).ledger.iter_events())
    assert projection["spikes"][spike_id]["status"] == (
        "partial_reviewed" if spike_verdict == "PARTIAL" else "reviewed"
    )
    assert projection["reviews"][review_id]["status"] == "satisfied"
    expected_review_events = (
        ("ReviewVerdictRecorded", "SpikePartialReviewed", "CandidateSpikePartialReviewed")
        if spike_verdict == "PARTIAL"
        else ("ReviewVerdictRecorded", "SpikeReviewed")
    )
    if spike_verdict == "PARTIAL":
        assert projection["candidates"][candidate_id]["status"] == "spike_revisit_eligible"
        assert projection["spikes"][spike_id]["attempt_status"] == "partial"
        assert projection["spikes"][spike_id]["lease_status"] == "released"
    assert tuple(event["event_type"] for event in tuple(runtime.ledger.iter_batches())[-1]) == expected_review_events
    tampered_review = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
    next(
        event
        for event in tampered_review
        if event["event_type"] in {"SpikeReviewed", "SpikePartialReviewed", "SpikeCancellationReviewed"}
        and event["stream_id"] == spike_id
    )["payload"]["review_id"] = assay_review_id
    with pytest.raises(IntegrityError, match="invalid Spike .*review"):
        replay_discovery(_rehash_events(tampered_review))
    if spike_verdict == "PASS":
        post_promotion_id = "dec_019fed25-b33e-7740-b280-6f661aaeff74"
        post_promotion = _command(
            "ProposePromotionDecision",
            post_promotion_id,
            0,
            {
                "row_id": "OR-026",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "decision_id": post_promotion_id,
                "review_id": review_id,
                "verdict_sha256": verdict_sha256,
                "w2_payload": promotion_proposed(post_promotion_id, "spike_to_preregistration"),
                "promotion_relation": _promotion_relation(
                    runtime,
                    decision_id=post_promotion_id,
                    candidate_id=candidate_id,
                    aggregate_id=spike_id,
                    review_id=review_id,
                    gate="spike_to_preregistration",
                ),
            },
        )
        reused_decision = _command(
            "ProposePromotionDecision",
            execution_id,
            2,
            {
                **deepcopy(post_promotion["payload"]),
                "decision_id": execution_id,
                "w2_payload": promotion_proposed(execution_id, "spike_to_preregistration"),
            },
        )
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="invalid Spike transition"):
            runtime.submit(reused_decision)
        assert tuple(runtime.ledger.iter_events()) == before
        foreign_verdict = deepcopy(post_promotion)
        foreign_verdict["payload"]["verdict_sha256"] = "f" * 64
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="invalid Spike transition"):
            runtime.submit(foreign_verdict)
        assert tuple(runtime.ledger.iter_events()) == before
        foreign_relation = deepcopy(post_promotion)
        foreign_relation["payload"]["promotion_relation"]["aggregate_ref"]["content_hash"] = "f" * 64
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="invalid Spike transition"):
            runtime.submit(foreign_relation)
        assert tuple(runtime.ledger.iter_events()) == before
        foreign_decision = deepcopy(post_promotion)
        foreign_decision["payload"]["w2_payload"]["new_decision_id"] = "dec_019fed25-b33e-7740-b280-ffffffffffff"
        with pytest.raises(IntegrityError, match="invalid Spike transition"):
            runtime.submit(foreign_decision)
        assert tuple(runtime.ledger.iter_events()) == before
        runtime.submit(post_promotion)
        post_resolution = _command(
            "ResolveDecision",
            post_promotion_id,
            1,
            {
                "row_id": "OR-027",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "decision_id": post_promotion_id,
                "review_id": review_id,
                "verdict_sha256": verdict_sha256,
                "w2_payload": promotion_resolved(post_promotion_id),
            },
        )
        wrong_gate_resolution = deepcopy(post_resolution)
        wrong_gate_resolution["payload"]["row_id"] = "OR-013"
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="invalid Spike transition"):
            runtime.submit(wrong_gate_resolution)
        assert tuple(runtime.ledger.iter_events()) == before
        runtime.submit(post_resolution)
        promoted = replay_discovery(runtime.ledger.iter_events())
        assert promoted["candidates"][candidate_id]["status"] == "preregistration_authorized"
        assert [
            tuple(event["event_type"] for event in batch) for batch in tuple(runtime.ledger.iter_batches())[-2:]
        ] == [
            ("DecisionProposed", "CandidatePromotionRequested"),
            ("DecisionResolved", "CandidatePromotionApplied"),
        ]
        tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
        next(
            event
            for event in tampered
            if event["event_type"] == "CandidatePromotionApplied"
            and event["payload"].get("promotion_gate") == "spike_to_preregistration"
        )["payload"]["next_candidate_state"] = "spike_planning_authorized"
        with pytest.raises(IntegrityError, match="invalid Candidate promotion application"):
            replay_discovery(_rehash_events(tampered))
        for event_type, identity_field, message in (
            ("DecisionProposed", "new_decision_id", "invalid Discovery decision proposal"),
            ("DecisionResolved", "decision_id", "invalid Discovery decision resolution"),
        ):
            tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
            next(
                event
                for event in tampered
                if event["event_type"] == event_type and event["stream_id"] == post_promotion_id
            )["payload"][identity_field] = "dec_019fed25-b33e-7740-b280-ffffffffffff"
            with pytest.raises(IntegrityError, match=message):
                replay_discovery(_rehash_events(tampered))
    if spike_verdict == "PARTIAL":
        _ingest_candidate(
            runtime,
            "obj_019fed25-b33e-7740-b280-6f661aaeff78",
            observation_id=predicate_observation_id,
            title="Objective Spike revisit evidence",
        )
        revisit_id = "dec_019fed25-b33e-7740-b280-6f661aaeff71"
        revisit_proposal = proposed(revisit_id, "spike_revisit")
        revisit_proposal["recommendation"] = "RETRY"
        revisit_proposal["options"] = ["RETRY", "PARK", "KILL"]
        revisit_proposal["governing_evidence_refs"] = [review_id]
        revisit_command = _command(
            "ProposeRevisitDecision",
            revisit_id,
            0,
            {
                "row_id": "OR-023",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "review_id": review_id,
                "decision_id": revisit_id,
                "w2_payload": revisit_proposal,
                "revisit_relation": _revisit_relation(
                    runtime,
                    decision_id=revisit_id,
                    candidate_id=candidate_id,
                    aggregate_id=spike_id,
                    review_id=review_id,
                    predicate_observation_id=predicate_observation_id,
                ),
            },
        )
        for mutation in ("foreign_review", "empty_options", "unbound_review", "foreign_predicate"):
            invalid = deepcopy(revisit_command)
            if mutation == "foreign_review":
                invalid["payload"]["review_id"] = "rev_019fed25-b33e-7740-b280-ffffffffffff"
            elif mutation == "empty_options":
                invalid["payload"]["w2_payload"]["options"] = []
            elif mutation == "unbound_review":
                invalid["payload"]["w2_payload"]["governing_evidence_refs"] = []
            else:
                invalid["payload"]["revisit_relation"]["satisfied_revisit_predicate_ref"]["id"] = review_id
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike revisit proposal"):
                runtime.submit(invalid)
            assert tuple(runtime.ledger.iter_events()) == before
        parked_projection = replay_discovery(runtime.ledger.iter_events())
        parked_projection["spikes"][spike_id]["status"] = "reviewed"
        parked_projection["candidates"][candidate_id]["status"] = "parked"
        predicate_position = parked_projection["source_observations"][predicate_observation_id]["global_position"]
        parked_projection["candidates"][candidate_id]["parked_at_global_position"] = predicate_position - 1
        assert [
            event_type for event_type, _, _ in runtime._prepare_spike(Command(revisit_command), parked_projection)
        ] == [
            "DecisionProposed",
            "SpikeRevisitRequested",
            "CandidateSpikeRevisitRequested",
        ]
        parked_projection["candidates"][candidate_id]["parked_at_global_position"] = predicate_position
        with pytest.raises(IntegrityError, match="invalid Spike revisit proposal"):
            runtime._prepare_spike(Command(revisit_command), parked_projection)
        runtime.submit(revisit_command)
        revisit_resolution = resolved(revisit_id)
        revisit_resolution["selected_option"] = "RETRY"
        runtime.submit(
            _command(
                "ResolveDecision",
                revisit_id,
                1,
                {
                    "row_id": "OR-024",
                    "candidate_id": candidate_id,
                    "spike_id": spike_id,
                    "decision_id": revisit_id,
                    "w2_payload": revisit_resolution,
                },
            )
        )
        retry_spike_id = "spk_019fed25-b33e-7740-b280-6f661aaeff72"
        retry_plan = deepcopy(plan_artifact)
        retry_plan["spike_id"] = retry_spike_id
        retry_plan["assay_promotion_decision_ref"]["id"] = revisit_id
        retry_plan_sha256 = sha256_hex(canonical_bytes(retry_plan))
        runtime.submit(
            _command(
                "RegisterSpikePlan",
                retry_spike_id,
                0,
                {
                    "row_id": "OR-025",
                    "candidate_id": candidate_id,
                    "old_spike_id": spike_id,
                    "spike_id": retry_spike_id,
                    "plan_sha256": retry_plan_sha256,
                    "plan_artifact": retry_plan,
                },
            )
        )
        retried = replay_discovery(runtime.ledger.iter_events())
        assert retried["spikes"][spike_id]["status"] == "superseded"
        assert retried["spikes"][retry_spike_id]["status"] == "approval_pending"
        assert retried["candidates"][candidate_id]["status"] == "spike_approval_pending"
        retry_execution_id = "dec_019fed25-b33e-7740-b280-6f661aaeff73"
        retry_plan_ref = _ref(retry_spike_id, 1, retry_plan_sha256)
        retry_execution_relation = {
            **deepcopy(execution_authority_relation),
            "decision_id": retry_execution_id,
            "spike_ref": retry_plan_ref,
            "plan_ref": retry_plan_ref,
            "route_ref": retry_plan_ref,
        }
        runtime.submit(
            _command(
                "ProposeSpikeExecutionDecision",
                retry_execution_id,
                0,
                {
                    "row_id": "OR-015",
                    "candidate_id": candidate_id,
                    "spike_id": retry_spike_id,
                    "decision_id": retry_execution_id,
                    "w2_payload": proposed(retry_execution_id, "spike_retry_execution"),
                    "execution_authority_relation": retry_execution_relation,
                },
            )
        )
        cancellation_projection = replay_discovery(runtime.ledger.iter_events())
        execution_decision = cancellation_projection["decisions"][retry_execution_id]
        cancellation_artifact = {
            "spike_id": retry_spike_id,
            "candidate_ref": candidate_ref,
            "plan_ref": retry_plan_ref,
            "attempt_ref": None,
            "lease_ref": None,
            "execution_proposal_ref": _ref(
                retry_execution_id,
                execution_decision["proposal_version"],
                execution_decision["proposal_event_hash"],
            ),
            "reason": "owner stops the retry before execution",
            "evidence_refs": [candidate_ref],
            "completed_scope": [],
            "unmet_scope": ["execution cancelled before start"],
            "restrictions": ["no_promotion"],
        }
        cancellation_sha256 = sha256_hex(canonical_bytes(cancellation_artifact))
        cancellation_command = _command(
            "CancelDiscoveryEvaluation",
            retry_spike_id,
            3,
            {
                "row_id": "OR-022",
                "evaluation_kind": "spike",
                "candidate_id": candidate_id,
                "spike_id": retry_spike_id,
                "cancellation_sha256": cancellation_sha256,
                "cancellation_artifact": cancellation_artifact,
            },
        )
        empty_reason = deepcopy(cancellation_command)
        empty_reason["payload"]["cancellation_artifact"]["reason"] = ""
        empty_reason["payload"]["cancellation_sha256"] = sha256_hex(
            canonical_bytes(empty_reason["payload"]["cancellation_artifact"])
        )
        before = tuple(runtime.ledger.iter_events())
        with pytest.raises(IntegrityError, match="invalid Spike cancellation transition"):
            runtime.submit(empty_reason)
        assert tuple(runtime.ledger.iter_events()) == before
        runtime.submit(cancellation_command)
        cancelled = replay_discovery(runtime.ledger.iter_events())
        assert cancelled["spikes"][retry_spike_id]["status"] == "cancelled"
        assert cancelled["candidates"][candidate_id]["status"] == "spike_cancelled"
        assert cancelled["decisions"][retry_execution_id]["status"] == "superseded_by_cancellation"
        assert tuple(event["event_type"] for event in tuple(runtime.ledger.iter_batches())[-1]) == (
            "SpikeExecutionProposalSupersededByCancellation",
            "SpikeCancelled",
            "CandidateEvaluationCancelled",
        )
        cancellation_events = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
        for missing_event_type in (
            "SpikeExecutionProposalSupersededByCancellation",
            "SpikeCancelled",
            "CandidateEvaluationCancelled",
        ):
            missing_pair_member = tuple(
                event
                for event in cancellation_events
                if not (
                    event["event_type"] == missing_event_type
                    and event["transaction_id"] == cancellation_events[-1]["transaction_id"]
                )
            )
            with pytest.raises(IntegrityError, match="cancellation"):
                replay_discovery(_reindex_and_rehash_events(missing_pair_member))
        substituted_hash = tuple(deepcopy(event) for event in cancellation_events)
        next(
            event
            for event in substituted_hash
            if event["event_type"] == "SpikeExecutionProposalSupersededByCancellation"
            and event["stream_id"] == retry_execution_id
        )["payload"]["cancellation_sha256"] = "f" * 64
        with pytest.raises(IntegrityError, match="invalid Spike execution proposal cancellation"):
            replay_discovery(_rehash_events(substituted_hash))
        substituted_subject = tuple(deepcopy(event) for event in cancellation_events)
        cancellation_event = next(
            event
            for event in substituted_subject
            if event["event_type"] == "SpikeCancelled" and event["stream_id"] == retry_spike_id
        )
        cancellation_event["payload"]["cancellation_artifact"]["plan_ref"]["content_hash"] = "f" * 64
        substituted_cancellation_hash = sha256_hex(
            canonical_bytes(cancellation_event["payload"]["cancellation_artifact"])
        )
        for event in substituted_subject:
            if event["command_id"] == cancellation_event["command_id"]:
                event["payload"]["cancellation_sha256"] = substituted_cancellation_hash
                if isinstance(event["payload"].get("cancellation_artifact"), dict):
                    event["payload"]["cancellation_artifact"] = deepcopy(
                        cancellation_event["payload"]["cancellation_artifact"]
                    )
        with pytest.raises(IntegrityError, match="invalid Spike cancellation"):
            replay_discovery(_rehash_events(substituted_subject))
        cancellation_review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff74"
        cancellation_contract = deepcopy(review_contract)
        cancellation_contract.update(
            new_review_id=cancellation_review_id,
            subject_ids=[retry_spike_id],
            subject_hashes=[cancellation_sha256],
            governing_refs=["W11:OR-040"],
            review_questions=["Is the exact Spike cancellation supported?"],
            required_evidence_refs=["evidence:spike-cancellation"],
        )
        runtime.submit(
            _command(
                "RequestDiscoveryOutcomeReview",
                cancellation_review_id,
                0,
                {
                    "row_id": "OR-040",
                    "candidate_id": candidate_id,
                    "spike_id": retry_spike_id,
                    "review_id": cancellation_review_id,
                    "subject_sha256": cancellation_sha256,
                    "review_contract": cancellation_contract,
                },
            )
        )
        cancellation_verdict = deepcopy(verdict)
        cancellation_verdict.update(
            review_id=cancellation_review_id,
            required_evidence_refs=["evidence:spike-cancellation"],
            unchanged_subject_sha256=cancellation_sha256,
        )
        cancellation_review = _command(
            "ReviewDiscoveryOutcome",
            cancellation_review_id,
            1,
            {
                "row_id": "OR-041",
                "candidate_id": candidate_id,
                "spike_id": retry_spike_id,
                "review_id": cancellation_review_id,
                "subject_sha256": cancellation_sha256,
                "review_verdict": cancellation_verdict,
            },
        )
        cancellation_review["actor_id"] = reviewer_id
        runtime.submit(cancellation_review)
        cancellation_reviewed = replay_discovery(runtime.ledger.iter_events())
        assert cancellation_reviewed["spikes"][retry_spike_id]["status"] == "cancellation_reviewed"
        assert cancellation_reviewed["candidates"][candidate_id]["status"] == "spike_revisit_eligible"
        for event_type in ("SpikeRevisitRequested", "SpikeRevisitResolved"):
            tampered = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
            next(event for event in tampered if event["event_type"] == event_type)["payload"]["candidate_id"] = (
                "obj_019fed25-b33e-7740-b280-ffffffffffff"
            )
            with pytest.raises(IntegrityError, match="invalid Discovery revisit"):
                replay_discovery(_rehash_events(tampered))
    for event_type, producer_type, identity_field, message in (
        ("SpikePlanned", "RegisterSpikePlan", "spike_id", "Spike identity collision"),
        ("DecisionProposed", "ProposePromotionDecision", "new_decision_id", "invalid Discovery decision proposal"),
        ("ReviewRequested", "RequestDiscoveryOutcomeReview", "new_review_id", "invalid Discovery review request"),
    ):
        cross_namespace = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
        minted = next(
            event
            for event in cross_namespace
            if event["event_type"] == event_type and event["command_type"] == producer_type
        )
        minted["stream_id"] = CATALOGUE_STREAM_ID
        minted["payload"][identity_field] = CATALOGUE_STREAM_ID
        with pytest.raises(IntegrityError, match=message):
            replay_discovery(_rehash_events(cross_namespace))
    for tampered_verdict in ("approve", "approve_with_conditions"):
        events = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
        verdict_event = next(
            event
            for event in events
            if event["event_type"] == "ReviewVerdictRecorded" and event["stream_id"] == review_id
        )
        verdict_event["actor_id"] = ACTOR_ID
        verdict_event["payload"]["reviewer_actor_id"] = ACTOR_ID
        verdict_event["payload"]["verdict"] = tampered_verdict
        verdict_event["payload"]["conditions"] = (
            [
                {
                    "gate_disposition": "non_blocking",
                    "owner_actor_id": ACTOR_ID,
                    "policy_id": "policy:spike-review",
                    "evidence_refs": ["evidence:provider-free"],
                }
            ]
            if tampered_verdict == "approve_with_conditions"
            else []
        )
        with pytest.raises(IntegrityError, match="invalid Discovery review verdict"):
            replay_discovery(_rehash_events(events))
