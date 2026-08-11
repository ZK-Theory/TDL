from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from datetime import UTC, datetime
import hashlib
import os
import uuid

import pytest

from research_system.discovery.runtime import DiscoveryRuntime, replay_discovery
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, IntegrityError
from research_system.ids import new_id
from research_system.store.ledger import EventLedger
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    ACTORS,
    PROJECT_ID,
    activate_lifecycle_grant,
    control_plane,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
TDA_RUNTIME_ROOT = Path(os.environ.get("TDL_REPOSITORY_ROOT", Path.home() / "TDL"))
TDA_VAULT_ROOT = Path(os.environ.get("TDA_VAULT_ROOT", TDA_RUNTIME_ROOT / "vault"))
CATALOGUE = REPO_ROOT / ".research-system" / "evals" / "expected" / "w11-portfolio-discovery-v1.json"
CATALOGUE_STREAM_ID = "obj_019fed25-b33e-7740-b280-000000000001"
ACTOR_ID = ACTORS["actor-a"]
GRANT_ID = "agr_019fed25-b33e-7740-b280-6f661aaeff58"
_HARNESSES = {}


def _runtime(tmp_path: Path) -> DiscoveryRuntime:
    harness = _HARNESSES.get(tmp_path)
    if harness is None:
        harness = control_plane(tmp_path)
        _HARNESSES[tmp_path] = harness
    root = tmp_path / "discovery"
    root.mkdir(exist_ok=True)

    class GovernedDiscoveryRuntime(DiscoveryRuntime):
        def submit(self, envelope):
            value = deepcopy(envelope)
            command_type = value["command_type"]
            subject_kind = {
                "ImportAcceptedW11CatalogueGenesis": "scope_definition",
                "RegisterCandidate": "scope_definition",
                "RequestAssay": "scope_definition",
                "RecordAssayScore": "scope_definition",
                "RequestDiscoveryOutcomeReview": "review",
                "ReviewDiscoveryOutcome": "review",
                "ProposePromotionDecision": "decision",
                "RegisterSpikePlan": "scope_definition",
                "ProposeSpikeExecutionDecision": "decision",
                "StartSpike": "scope_definition",
                "RecordSpikeVerdict": "scope_definition",
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
        EventLedger(root, PROJECT_ID, harness.schemas),
        harness.schemas,
        catalogue_path=CATALOGUE,
        authority_resolver=harness.authority_resolver,
        clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
        repository_root=REPO_ROOT,
        root_tokens={
            "$REPOSITORY_CONTRACT_ROOT": TDA_RUNTIME_ROOT / ".research-system/contracts/wp6-4",
            "$TDA_VAULT_ROOT": TDA_VAULT_ROOT,
        },
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
        "payload": payload,
        "global_position": 1,
        "previous_event_hash": "0" * 64,
    }
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    with pytest.raises(IntegrityError, match=message):
        replay_discovery((event,))


def test_genesis_rejects_wrong_actor_scope_and_expired_grant_without_mutation(tmp_path: Path) -> None:
    harness = control_plane(tmp_path)
    root = tmp_path / "governed-discovery"
    root.mkdir()
    runtime = DiscoveryRuntime(
        root,
        EventLedger(root, PROJECT_ID, harness.schemas),
        harness.schemas,
        catalogue_path=CATALOGUE,
        authority_resolver=harness.authority_resolver,
        clock=lambda: datetime(2026, 8, 2, tzinfo=UTC),
        repository_root=REPO_ROOT,
        root_tokens={
            "$REPOSITORY_CONTRACT_ROOT": TDA_RUNTIME_ROOT / ".research-system/contracts/wp6-4",
            "$TDA_VAULT_ROOT": TDA_VAULT_ROOT,
        },
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
            "source_observation_refs": ["obs:tda-scale:v1"],
            "title": "TDA-scale dossier candidate",
        },
    }

    with pytest.raises(IntegrityError, match="W11 genesis is required"):
        runtime.submit(candidate)
    assert tuple(runtime.ledger.iter_events()) == ()

    runtime.submit(_genesis())
    receipt = runtime.submit(candidate)
    duplicate = runtime.submit(deepcopy(candidate))

    assert receipt.status == "accepted"
    assert duplicate == receipt
    restarted = _runtime(tmp_path)
    projection = replay_discovery(restarted.ledger.iter_events())
    assert projection["candidates"][candidate_id] == {
        "candidate_id": candidate_id,
        "revision": 1,
        "content_sha256": "1" * 64,
        "status": "registered",
        "source_observation_refs": ["obs:tda-scale:v1"],
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


def test_assay_positive_lifecycle_is_atomic_durable_and_replay_equivalent(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff58"
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff59"
    review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff5a"
    runtime.submit(_genesis())
    runtime.submit(
        _command(
            "RegisterCandidate",
            candidate_id,
            0,
            {
                "candidate_id": candidate_id,
                "revision": 1,
                "content_sha256": "1" * 64,
                "source_observation_refs": ["obs:tda-scale:v1"],
                "title": "TDA-scale dossier candidate",
            },
        )
    )

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
                "candidate_sha256": "1" * 64,
                "assay_bar_acceptance_sha256": "2" * 64,
                "producer_relation_sha256": "3" * 64,
            },
        )
    )
    scored = runtime.submit(
        _command(
            "RecordAssayScore",
            assay_id,
            2,
            {
                "row_id": "OR-004",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "scorecard_sha256": "4" * 64,
                "producer_relation_sha256": "3" * 64,
            },
        )
    )
    review_requested = runtime.submit(
        _command(
            "RequestDiscoveryOutcomeReview",
            review_id,
            0,
            {
                "row_id": "OR-034",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "review_id": review_id,
                "subject_sha256": "4" * 64,
                "review_contract": {
                    "review_type": "provenance",
                    "new_review_id": review_id,
                    "subject_ids": [assay_id],
                    "subject_hashes": ["4" * 64],
                    "governing_refs": ["W11:OR-034"],
                    "review_questions": ["Does the exact Assay evidence satisfy the accepted bar?"],
                    "required_evidence_refs": ["scorecard:exact"],
                    "required_lanes": ["provenance"],
                    "reviewer_capability": ["assay-independent-review"],
                    "required_independence_grade": "independent",
                    "visibility_policy": "owner-visible",
                    "allowed_verdicts": ["approve", "changes_requested", "reject", "unable_to_verify"],
                    "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
                    "deadline": "2026-08-11T20:00:00Z",
                    "escalation_rule": "owner-ruling",
                },
            },
        )
    )
    reviewed = runtime.submit(
        _command(
            "ReviewDiscoveryOutcome",
            review_id,
            1,
            {
                "row_id": "OR-006",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "review_id": review_id,
                "subject_sha256": "4" * 64,
                "verdict": "approve",
                "review_verdict": {
                    "review_id": review_id,
                    "verdict": "approve",
                    "findings": [],
                    "required_evidence_refs": ["scorecard:exact"],
                    "limitations": [],
                    "conditions": [],
                    "reviewer_actor_id": "act_019fed25-b33e-7740-b280-6f661aaeff5b",
                    "reviewer_profile": "independent-assay-reviewer",
                    "reviewer_session": "session-wp66-assay-review",
                    "reviewer_model_metadata": "independent-test-reviewer",
                    "context_manifest_id": "ctx_019fed25-b33e-7740-b280-6f661aaeff5c",
                    "context_manifest_sha256": "5" * 64,
                    "unchanged_subject_sha256": "4" * 64,
                    "producing_attempt_id": "att_019fed25-b33e-7740-b280-6f661aaeff5d",
                    "trace_visibility_evidence_refs": ["trace:assay-review"],
                    "computed_independence_grade": "independent",
                },
            },
        )
    )

    assert [requested.status, scored.status, review_requested.status, reviewed.status] == ["accepted"] * 4
    batches = tuple(runtime.ledger.iter_batches())
    assert [tuple(event["event_type"] for event in batch) for batch in batches[-4:]] == [
        ("AssayRequested", "AssayEvidenceCollectionOpened", "CandidateAssayRequested"),
        ("AssayScored", "CandidateAssayLinked"),
        ("ReviewRequested", "AssayOutcomeReviewRequested"),
        ("ReviewVerdictRecorded", "AssayReviewed"),
    ]
    projection = replay_discovery(_runtime(tmp_path).ledger.iter_events())
    assert projection["assays"][assay_id]["status"] == "reviewed"
    assert projection["assays"][assay_id]["scorecard_sha256"] == "4" * 64
    assert projection["candidates"][candidate_id]["status"] == "assay_scored"
    assert projection["reviews"][review_id]["status"] == "satisfied"


def test_spike_positive_lifecycle_reaches_reviewed_atomically_and_without_provider_execution(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff68"
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff69"
    spike_id = "spk_019fed25-b33e-7740-b280-6f661aaeff6a"
    promotion_id = "dec_019fed25-b33e-7740-b280-6f661aaeff6b"
    execution_id = "dec_019fed25-b33e-7740-b280-6f661aaeff6c"
    review_id = "rev_019fed25-b33e-7740-b280-6f661aaeff6d"
    runtime.submit(_genesis())
    runtime.submit(
        _command(
            "RegisterCandidate",
            candidate_id,
            0,
            {
                "candidate_id": candidate_id,
                "revision": 1,
                "content_sha256": "1" * 64,
                "source_observation_refs": ["obs:spike"],
                "title": "Spike candidate",
            },
        )
    )
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
                "candidate_sha256": "1" * 64,
                "assay_bar_acceptance_sha256": "2" * 64,
                "producer_relation_sha256": "3" * 64,
            },
        )
    )
    runtime.submit(
        _command(
            "RecordAssayScore",
            assay_id,
            2,
            {
                "row_id": "OR-004",
                "candidate_id": candidate_id,
                "assay_id": assay_id,
                "scorecard_sha256": "4" * 64,
                "producer_relation_sha256": "3" * 64,
            },
        )
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

    commands = [
        _command(
            "ProposePromotionDecision",
            promotion_id,
            0,
            {
                "row_id": "OR-012",
                "candidate_id": candidate_id,
                "decision_id": promotion_id,
                "w2_payload": proposed(promotion_id, "promotion"),
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
                "w2_payload": resolved(promotion_id),
            },
        ),
        _command(
            "RegisterSpikePlan",
            spike_id,
            0,
            {"row_id": "OR-014", "candidate_id": candidate_id, "spike_id": spike_id, "plan_sha256": "5" * 64},
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
                "attempt_id": "att_019fed25-b33e-7740-b280-6f661aaeff6e",
                "lease_id": "lease:exact",
            },
        ),
        _command(
            "RecordSpikeVerdict",
            spike_id,
            5,
            {
                "row_id": "OR-018",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "verdict": "PASS",
                "verdict_sha256": "6" * 64,
                "evidence_refs": ["evidence:provider-free"],
            },
        ),
    ]
    for command in commands:
        assert runtime.submit(command).status == "accepted"
    review_contract = {
        "review_type": "provenance",
        "new_review_id": review_id,
        "subject_ids": [spike_id],
        "subject_hashes": ["6" * 64],
        "governing_refs": ["W11:OR-036"],
        "review_questions": ["Is the exact Spike verdict supported?"],
        "required_evidence_refs": ["evidence:provider-free"],
        "required_lanes": ["provenance"],
        "reviewer_capability": ["spike-independent-review"],
        "required_independence_grade": "independent",
        "visibility_policy": "owner-visible",
        "allowed_verdicts": ["approve", "changes_requested", "reject", "unable_to_verify"],
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
                "row_id": "OR-036",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "review_id": review_id,
                "subject_sha256": "6" * 64,
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
        "reviewer_actor_id": ACTOR_ID,
        "reviewer_profile": "independent-spike-reviewer",
        "reviewer_session": "session-spike",
        "reviewer_model_metadata": "test",
        "context_manifest_id": "ctx_019fed25-b33e-7740-b280-6f661aaeff6f",
        "context_manifest_sha256": "7" * 64,
        "unchanged_subject_sha256": "6" * 64,
        "producing_attempt_id": "att_019fed25-b33e-7740-b280-6f661aaeff6e",
        "trace_visibility_evidence_refs": ["trace:spike"],
        "computed_independence_grade": "independent",
    }
    runtime.submit(
        _command(
            "ReviewDiscoveryOutcome",
            review_id,
            1,
            {
                "row_id": "OR-020",
                "candidate_id": candidate_id,
                "spike_id": spike_id,
                "review_id": review_id,
                "subject_sha256": "6" * 64,
                "review_verdict": verdict,
            },
        )
    )

    projection = replay_discovery(_runtime(tmp_path).ledger.iter_events())
    assert projection["spikes"][spike_id]["status"] == "reviewed"
    assert projection["reviews"][review_id]["status"] == "satisfied"
    assert tuple(event["event_type"] for event in tuple(runtime.ledger.iter_batches())[-1]) == (
        "ReviewVerdictRecorded",
        "SpikeReviewed",
    )
