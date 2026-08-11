from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from datetime import UTC, datetime
import hashlib
import json
import os
import uuid

import pytest

from research_system.discovery.runtime import DiscoveryRuntime, replay_discovery
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import replay_control_plane
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
ASSAY_AUTHORITY_ACTORS = tuple(f"act_019fed25-b33e-7740-b280-{number:012d}" for number in range(201, 206))
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
                "RegisterAssayRubricContent": "scope_definition",
                "RegisterAssayEvidenceScopeContent": "scope_definition",
                "RecordAssayBarStaleness": "scope_definition",
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


def _accept_assay_bar(runtime: DiscoveryRuntime) -> tuple[str, str]:
    rubric = json.loads((REPO_ROOT / ASSAY_RUBRIC_PATH).read_bytes())
    scope = json.loads((REPO_ROOT / ASSAY_SCOPE_PATH).read_bytes())
    observer, proposer, reviewer, owner = ASSAY_AUTHORITY_ACTORS[:4]
    review_id = "rev_019fed25-b33e-7740-b280-000000000105"
    decision_id = "dec_019fed25-b33e-7740-b280-000000000107"
    producer_ref = {"id": ACTOR_ID, "record_revision": 1, "content_hash": "3" * 64}
    steps = (
        (
            "RegisterAssayRubricContent",
            ACTOR_ID,
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
            ACTOR_ID,
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
            observer,
            rubric["record_id"],
            1,
            {"row_id": "OR-103", "authority_kind": "assay_bar"},
        ),
        (
            "ObserveW11AuthorityFile",
            observer,
            scope["record_id"],
            1,
            {"row_id": "OR-104", "authority_kind": "assay_bar"},
        ),
        (
            "RequestW11AuthorityReview",
            proposer,
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
            proposer,
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
        assert runtime.submit(command).status == "accepted"
    bar = replay_discovery(runtime.ledger.iter_events())["assay_bar_authority"]
    assert bar["status"] == "accepted"
    return bar["acceptance_sha256"], bar["producer_relation_sha256"]


def _scorecard(candidate_id: str, assay_id: str, candidate_sha256: str, relation_sha256: str) -> dict[str, object]:
    ref = {"id": "evidence:exact", "record_revision": 1, "content_hash": "6" * 64}
    return {
        "schema_id": "ars://portfolio/assay-scorecard",
        "schema_version": "1.0.0",
        "candidate_ref": {"id": candidate_id, "record_revision": 1, "content_hash": candidate_sha256},
        "assay_id": assay_id,
        "assay_requested_event_ref": ref,
        "assay_relation_hash": relation_sha256,
        "rubric_ref": ref,
        "scope_ref": ref,
        "assay_bar_acceptance_ref": ref,
        "file_observation_refs": [ref, {**ref, "id": "evidence:scope"}],
        "producer_relation_ref": ref,
        "axis_results": [
            {
                "axis_id": "closure",
                "axis_kind": "gate",
                "value": True,
                "rationale": "Exact fixture evidence closes the declared axis.",
                "evidence_refs": [ref],
                "unmet_condition_codes": [],
                "validator_id": "validator:closure",
                "validator_hash": "7" * 64,
            }
        ],
        "required_axis_set_hash": "8" * 64,
        "observed_axis_set_hash": "8" * 64,
        "mechanical_recommendation": "PROMOTE",
        "rule_evaluation_ref": ref,
        "limitations": [],
        "prohibited_inferences": ["The scorecard does not itself authorize promotion."],
        "producer_actor_id": ACTOR_ID,
        "producer_profile_ref": ref,
        "producer_context_ref": ref,
        "review_requirements": ["independent-review"],
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
    runtime.submit(
        _command(
            "RegisterCandidate",
            candidate_id,
            0,
            {
                "candidate_id": candidate_id,
                "revision": 1,
                "content_sha256": "1" * 64,
                "source_observation_refs": ["obs:malformed-replay"],
                "title": "Malformed replay probe",
            },
        )
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
                "candidate_sha256": "1" * 64,
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


@pytest.mark.parametrize(
    ("verdict", "review_status", "assay_status", "terminal_events"),
    [
        ("approve", "satisfied", "reviewed", ("ReviewVerdictRecorded", "AssayReviewed")),
        ("changes_requested", "changes_requested", "scored", ("ReviewVerdictRecorded",)),
    ],
)
def test_assay_verdict_lifecycle_is_atomic_durable_and_replay_equivalent(
    tmp_path: Path,
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
    scorecard = _scorecard(candidate_id, assay_id, "1" * 64, "3" * 64)
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))
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

    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    scorecard = _scorecard(candidate_id, assay_id, "1" * 64, producer_sha256)
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))

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
                "assay_bar_acceptance_sha256": bar_sha256,
                "producer_relation_sha256": producer_sha256,
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
                "scorecard_sha256": scorecard_sha256,
                "scorecard_artifact": scorecard,
                "producer_relation_sha256": producer_sha256,
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
    )
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
    if verdict == "approve":
        for tampered_verdict in ("approve", "approve_with_conditions"):
            events = tuple(deepcopy(event) for event in runtime.ledger.iter_events())
            verdict_event = next(event for event in events if event["event_type"] == "ReviewVerdictRecorded")
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
    attempt_id = C1_ATTEMPT_ID
    lease_id = C1_LEASE_ID
    resource_grant_id = C1_RESOURCE_GRANT_ID
    _seed_running_attempt(_HARNESSES[tmp_path])
    attempt_sha256 = sha256_hex(canonical_bytes(_HARNESSES[tmp_path].replay().stream_states[attempt_id]))
    scorecard = _scorecard(candidate_id, assay_id, "1" * 64, "3" * 64)
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))
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
    bar_sha256, producer_sha256 = _accept_assay_bar(runtime)
    scorecard = _scorecard(candidate_id, assay_id, "1" * 64, producer_sha256)
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))
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
                "assay_bar_acceptance_sha256": bar_sha256,
                "producer_relation_sha256": producer_sha256,
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
    runtime.submit(
        _command(
            "RegisterCandidate",
            foreign_candidate_id,
            0,
            {
                "candidate_id": foreign_candidate_id,
                "revision": 1,
                "content_sha256": "a" * 64,
                "source_observation_refs": ["obs:foreign"],
                "title": "Foreign candidate",
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

    candidate_ref = {"id": candidate_id, "record_revision": 1, "content_hash": "1" * 64}
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
        if row_id == "OR-015":
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
        if row_id == "OR-018" and spike_verdict == "PASS":
            unevaluated = deepcopy(command)
            unevaluated_artifact = unevaluated["payload"]["verdict_artifact"]
            unevaluated_artifact["success_predicates"][0]["status"] = "unable_to_evaluate"
            unevaluated["payload"]["verdict_sha256"] = sha256_hex(canonical_bytes(unevaluated_artifact))
            before = tuple(runtime.ledger.iter_events())
            with pytest.raises(IntegrityError, match="invalid Spike transition"):
                runtime.submit(unevaluated)
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
        if row_id == "OR-017":
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
    if spike_verdict == "PARTIAL":
        operational = replay_control_plane(runtime.operational_ledger.snapshot().events)
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
        "governing_refs": ["W11:OR-036"],
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
                "row_id": "OR-036",
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
            "row_id": "OR-020",
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "review_id": review_id,
            "subject_sha256": verdict_sha256,
            "review_verdict": verdict,
        },
    )
    spike_review["actor_id"] = reviewer_id
    runtime.submit(spike_review)

    projection = replay_discovery(_runtime(tmp_path).ledger.iter_events())
    assert projection["spikes"][spike_id]["status"] == "reviewed"
    assert projection["reviews"][review_id]["status"] == "satisfied"
    expected_review_events = ("ReviewVerdictRecorded", "SpikeReviewed")
    if spike_verdict == "PARTIAL":
        expected_review_events += ("CandidateSpikePartialReviewed",)
        assert projection["candidates"][candidate_id]["status"] == "spike_revisit_pending"
        assert projection["spikes"][spike_id]["attempt_status"] == "partial"
        assert projection["spikes"][spike_id]["lease_status"] == "released"
    assert tuple(event["event_type"] for event in tuple(runtime.ledger.iter_batches())[-1]) == expected_review_events
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
