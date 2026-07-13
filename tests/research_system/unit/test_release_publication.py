from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, IntegrityError, SchemaError
from research_system.evals.release_publication import (
    BoundReleasePublicationEvidence,
    PublicationEvidenceError,
    ReleasePublicationRequest,
    verify_release_publication,
    verify_replayed_release,
)
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventDraft, EventLedger
from tests.research_system.factories import control_plane


ROOT = Path(__file__).resolve().parents[3]
PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
DECISION_ID = "rgd_01978abc-1003-7000-8000-000000001003"
MANIFEST_REF = "art_01978abc-2001-7000-8000-000000002001"
CONTROL_REF = "art_01978abc-2002-7000-8000-000000002002"
GRANT_ID = "agr_01978abc-1001-7000-8000-000000001001"
EVENT_ID = "evt_01978abc-2003-7000-8000-000000002003"
COMMAND_ID = "cmd_01978abc-2004-7000-8000-000000002004"
BATCH_ID = "txb_01978abc-2005-7000-8000-000000002005"


def publication_request() -> dict:
    return {
        "schema": "ars://evals/release-publication-request",
        "project_id": PROJECT_ID,
        "release_decision_id": DECISION_ID,
        "evaluation_runs_manifest_ref": MANIFEST_REF,
        "control_binding_ref": CONTROL_REF,
        "publication_authority_grant_id": GRANT_ID,
        "publication_authority_sha256": "a" * 64,
        "idempotency_key": "release-publication:synthetic-p0",
    }


def publication_command(command_id: str = COMMAND_ID) -> dict:
    return {
        "command_id": command_id,
        "command_type": "PublishReleaseGateDecision",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-13T12:00:00Z",
        "actor_id": "act_01978abc-1002-7000-8000-000000001002",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": GRANT_ID,
        "target_stream_id": DECISION_ID,
        "expected_stream_version": 0,
        "idempotency_key": "release-publication:synthetic-p0",
        "correlation_id": "synthetic-publication",
        "causation_id": None,
        "reason": "record the blocked synthetic P0 decision",
        "evidence_refs": [MANIFEST_REF, CONTROL_REF],
        "payload": publication_request(),
    }


def published_decision() -> dict:
    return {
        "schema_id": "ars://evals/release-gate-decision",
        "schema_version": "1.0.0",
        "release_gate_decision_id": DECISION_ID,
        "coverage_manifest_id": "ars-eval-p0-coverage-v1",
        "baseline_identity": "reference-pair-p0",
        "candidate_identity": "foundation-p0",
        "evidence_snapshot_hash": "b" * 64,
        "required_verdicts": [],
        "critical_failures": [],
        "parity_status": "pass",
        "operations_status": "pass",
        "decision": "blocked",
        "decided_at": "2026-07-13T12:00:00Z",
        "canonical_event_ref": EVENT_ID,
        "policy_parity_report_id": "ppr_" + "c" * 64,
        "policy_parity_report_hash": "c" * 64,
        "policy_control_applicability_id": "pca_" + "d" * 64,
        "policy_control_applicability_hash": "d" * 64,
        "exception_policy_id": None,
        "exception_policy_hash": None,
        "exception_scope": None,
        "exception_expiry": None,
        "disabled_or_constrained_capability": None,
        "rationale": None,
        "human_authority_id": None,
        "supersedes": None,
    }


def published_event() -> dict:
    return {
        "event_id": EVENT_ID,
        "event_type": "ReleaseGateDecisionPublished",
        "schema_id": "ars://core/event/ReleaseGateDecisionPublished",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "stream_id": DECISION_ID,
        "stream_version": 1,
        "global_position": 3,
        "transaction_id": BATCH_ID,
        "transaction_index": 1,
        "transaction_count": 1,
        "command_id": COMMAND_ID,
        "command_type": "PublishReleaseGateDecision",
        "idempotency_key": "release-publication:synthetic-p0",
        "command_payload_hash": "e" * 64,
        "correlation_id": "synthetic-publication",
        "causation_id": None,
        "actor_id": "act_01978abc-1002-7000-8000-000000001002",
        "authority_grant_id": GRANT_ID,
        "occurred_at": None,
        "recorded_at": "2026-07-13T12:00:01Z",
        "payload": {
            "release_decision": published_decision(),
            "source_decision_sha256": "f" * 64,
            "evaluation_runs_manifest_ref": MANIFEST_REF,
            "evaluation_runs_manifest_sha256": "1" * 64,
            "control_binding_ref": CONTROL_REF,
            "control_binding_sha256": "2" * 64,
            "publication_authority_grant_id": GRANT_ID,
            "publication_authority_sha256": "a" * 64,
            "gate5_authorized": False,
            "candidate_status": "blocked",
        },
        "previous_event_hash": "0" * 64,
        "event_hash": "3" * 64,
    }


def source_decision() -> dict:
    return {**published_decision(), "canonical_event_ref": "unpublished:p0"}


def evidence_resolver(*, derived: dict | None = None, gate: object = False):
    source = source_decision()
    manifest = {
        "schema_id": "ars://evals/release-publication-evidence",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "release_decision": source,
    }
    control = {
        "schema_id": "ars://evals/release-control-binding",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "store_identity": "4" * 64,
        "coverage_manifest_id": source["coverage_manifest_id"],
    }
    return BoundReleasePublicationEvidence(
        evaluation_runs_manifest_ref=MANIFEST_REF,
        evaluation_runs_manifest=manifest,
        control_binding_ref=CONTROL_REF,
        control_binding=control,
        rederive=lambda _manifest, _control: (
            source if derived is None else derived,
            gate,
        ),
    )


def test_release_publication_request_has_a_strict_registered_contract() -> None:
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    registry.validate(
        "ars://evals/release-publication-request",
        publication_request(),
    )


def test_release_publication_request_model_is_frozen_and_exact() -> None:
    request = ReleasePublicationRequest.from_dict(publication_request())
    assert request.release_decision_id == DECISION_ID
    assert request.to_dict() == publication_request()
    with pytest.raises(FrozenInstanceError):
        request.project_id = "prj_01978abc-9999-7000-8000-000000009999"


def test_release_event_has_a_strict_full_registered_contract() -> None:
    SchemaRegistry(ROOT / ".research-system" / "schemas").validate(
        "ars://core/event/ReleaseGateDecisionPublished",
        published_event(),
    )


def test_full_canonical_evidence_is_rederived_and_bound() -> None:
    verified = verify_release_publication(
        ReleasePublicationRequest.from_dict(publication_request()),
        evidence_resolver(),
        SchemaRegistry(ROOT / ".research-system" / "schemas"),
    )
    payload = verified.payload_for(EVENT_ID)
    assert payload["release_decision"]["canonical_event_ref"] == EVENT_ID
    assert payload["release_decision"]["decision"] == "blocked"
    assert payload["gate5_authorized"] is False
    assert payload["candidate_status"] == "blocked"


def test_semantic_rederivation_mismatch_fails_closed() -> None:
    changed = source_decision()
    changed["evidence_snapshot_hash"] = "9" * 64
    with pytest.raises(PublicationEvidenceError, match="re-derived decision mismatch"):
        verify_release_publication(
            ReleasePublicationRequest.from_dict(publication_request()),
            evidence_resolver(derived=changed),
            SchemaRegistry(ROOT / ".research-system" / "schemas"),
        )


def test_ledger_allocates_release_event_identity_before_payload_finalization(
    tmp_path,
) -> None:
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    verified = verify_release_publication(
        ReleasePublicationRequest.from_dict(publication_request()),
        evidence_resolver(),
        schemas,
    )
    base = {
        key: value
        for key, value in published_event().items()
        if key
        not in {
            "event_id",
            "project_id",
            "stream_version",
            "global_position",
            "transaction_id",
            "transaction_index",
            "transaction_count",
            "recorded_at",
            "payload",
            "previous_event_hash",
            "event_hash",
        }
    }
    ledger = EventLedger(tmp_path / "control", PROJECT_ID)
    receipt = ledger.append(
        [
            EventDraft(
                base,
                lambda allocated: verified.payload_for(allocated.event_id),
                schemas.validate,
                (
                    "ars://core/event",
                    "ars://core/event/ReleaseGateDecisionPublished",
                ),
            )
        ]
    )
    event = tuple(ledger.iter_events())[-1]
    assert receipt["event_ids"] == [event["event_id"]]
    assert event["payload"]["release_decision"]["canonical_event_ref"] == event["event_id"]


def test_valid_publication_request_fails_closed_without_authorizer(tmp_path) -> None:
    harness = control_plane(tmp_path)
    receipt = harness.service.submit(publication_command())
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_publication_authorizer_unavailable"
    assert tuple(harness.ledger.iter_events()) == ()


def test_authorized_verified_command_publishes_one_self_referential_event(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    receipt = harness.service.submit(publication_command())
    assert receipt.status == "accepted"
    events = tuple(harness.ledger.iter_events())
    assert len(events) == 1
    assert events[0]["event_type"] == "ReleaseGateDecisionPublished"
    assert events[0]["stream_id"] == DECISION_ID
    assert events[0]["payload"]["release_decision"]["canonical_event_ref"] == events[0]["event_id"]


def test_rejected_exact_retry_with_new_command_id_returns_original_outcome(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    original = harness.service.submit(publication_command())
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    retry = publication_command(
        "cmd_01978abc-2006-7000-8000-000000002006"
    )
    assert harness.service.submit(retry) == original
    assert tuple(harness.ledger.iter_events()) == ()


def test_scoped_retry_with_changed_payload_returns_conflict_without_event(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.submit(publication_command())
    changed = publication_command(
        "cmd_01978abc-2007-7000-8000-000000002007"
    )
    changed_ref = "art_01978abc-2008-7000-8000-000000002008"
    changed["payload"] = {
        **changed["payload"],
        "evaluation_runs_manifest_ref": changed_ref,
    }
    changed["evidence_refs"] = [changed_ref, CONTROL_REF]
    receipt = harness.service.submit(changed)
    assert receipt.status == "conflict"
    assert receipt.reason_code == "idempotency_conflict"
    assert tuple(harness.ledger.iter_events()) == ()


def test_accepted_exact_retry_with_new_command_id_returns_original_event(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    original = harness.service.submit(publication_command())
    retry = publication_command(
        "cmd_01978abc-2009-7000-8000-000000002009"
    )
    assert harness.service.submit(retry) == original
    assert len(tuple(harness.ledger.iter_events())) == 1


@pytest.mark.parametrize(
    ("target", "value"),
    [
        ("request_extra", True),
        ("request_hash", "A" * 64),
        ("request_ref", "C:/tmp/decision.json"),
        ("request_float", 1.5),
        ("event_payload_schema", "forbidden"),
        ("event_secret", "forbidden"),
        ("event_authorized", True),
        ("event_sentinel", "unpublished:p0"),
    ],
)
def test_publication_schemas_reject_forbidden_surfaces(target, value) -> None:
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    if target.startswith("request_"):
        document = publication_request()
        if target == "request_extra":
            document["authorized"] = value
        elif target == "request_hash":
            document["publication_authority_sha256"] = value
        elif target == "request_ref":
            document["evaluation_runs_manifest_ref"] = value
        else:
            document["idempotency_key"] = value
        schema_id = "ars://evals/release-publication-request"
    else:
        document = published_event()
        if target == "event_payload_schema":
            document["payload_schema"] = value
        elif target == "event_secret":
            document["payload"]["secret"] = value
        elif target == "event_authorized":
            document["payload"]["gate5_authorized"] = value
        else:
            document["payload"]["release_decision"][
                "canonical_event_ref"
            ] = value
        schema_id = "ars://core/event/ReleaseGateDecisionPublished"
    with pytest.raises(SchemaError):
        registry.validate(schema_id, document)


def test_direct_raw_release_event_cannot_bypass_ledger_finalizer(tmp_path) -> None:
    event = published_event()
    raw = {
        key: value
        for key, value in event.items()
        if key
        not in {
            "event_id",
            "project_id",
            "stream_version",
            "global_position",
            "transaction_id",
            "transaction_index",
            "transaction_count",
            "recorded_at",
            "previous_event_hash",
            "event_hash",
        }
    }
    with pytest.raises(ArsError, match="requires a ledger event finalizer"):
        EventLedger(tmp_path / "control", PROJECT_ID).append([raw])


def test_replay_requires_schema_validation_and_rejects_self_reference_tamper(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    harness.service.submit(publication_command())
    event = tuple(harness.ledger.iter_events())[-1]
    with pytest.raises(IntegrityError, match="schema validator unavailable"):
        replay([event])
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    assert replay([event], schema_registry=schemas)["release_decisions"][
        DECISION_ID
    ]["candidate_status"] == "blocked"
    tampered = deepcopy(event)
    tampered["payload"]["release_decision"]["canonical_event_ref"] = (
        "evt_01978abc-2010-7000-8000-000000002010"
    )
    unsigned = dict(tampered)
    unsigned.pop("event_hash")
    tampered["event_hash"] = sha256_hex(canonical_bytes(unsigned))
    with pytest.raises(IntegrityError, match="identity or disposition"):
        replay([tampered], schema_registry=schemas)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("source_hash", "source hash mismatch"),
        ("previous_hash", "hash-chain mismatch"),
    ],
)
def test_replay_rejects_release_source_and_chain_tamper(
    tmp_path,
    tamper,
    message,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    harness.service.submit(publication_command())
    event = deepcopy(tuple(harness.ledger.iter_events())[-1])
    if tamper == "source_hash":
        event["payload"]["source_decision_sha256"] = "0" * 64
    else:
        event["previous_event_hash"] = "1" * 64
    unsigned = dict(event)
    unsigned.pop("event_hash")
    event["event_hash"] = sha256_hex(canonical_bytes(unsigned))
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    with pytest.raises(IntegrityError, match=message):
        replay([event], schema_registry=schemas)


@pytest.mark.parametrize(
    "tamper",
    [
        "sentinel",
        "unknown_event",
        "foreign_project",
        "projection_source",
        "authorized",
        "released",
    ],
)
def test_release_resolution_rejects_sentinel_unknown_foreign_and_projection_tamper(
    tamper,
) -> None:
    source = source_decision()
    record = {
        "project_id": PROJECT_ID,
        "release_decision_id": DECISION_ID,
        "release_decision": published_decision(),
        "source_decision_sha256": sha256_hex(canonical_bytes(source)),
        "gate5_authorized": False,
        "candidate_status": "blocked",
        "event_id": EVENT_ID,
    }
    projection = {"release_decisions": {DECISION_ID: record}}
    if tamper == "sentinel":
        source["canonical_event_ref"] = EVENT_ID
    elif tamper == "unknown_event":
        projection["release_decisions"] = {}
    elif tamper == "foreign_project":
        record["project_id"] = "prj_01978abc-9999-7000-8000-000000009999"
    elif tamper == "projection_source":
        record["source_decision_sha256"] = "0" * 64
    elif tamper == "authorized":
        record["gate5_authorized"] = True
    else:
        record["candidate_status"] = "released"
    with pytest.raises(PublicationEvidenceError):
        verify_replayed_release(source, projection, PROJECT_ID)


@pytest.mark.parametrize(
    "failure",
    [
        "authority actor mismatch",
        "authority command mismatch",
        "authority grant expired",
        "authority grant revoked",
        "authority subject scope mismatch",
    ],
)
def test_authority_failures_return_stable_unauthorized_receipts(
    tmp_path,
    failure,
) -> None:
    harness = control_plane(tmp_path)

    def reject(*_args):
        raise ArsError(failure)

    harness.service.authority_resolver = SimpleNamespace(resolve=reject)
    harness.service.release_publication_evidence = evidence_resolver()
    receipt = harness.service.submit(publication_command())
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_publication_unauthorized"
    assert tuple(harness.ledger.iter_events()) == ()


def test_foreign_project_binding_is_a_stable_rejection(tmp_path) -> None:
    harness = control_plane(tmp_path)
    command = publication_command()
    command["payload"] = {
        **command["payload"],
        "project_id": "prj_01978abc-2011-7000-8000-000000002011",
    }
    receipt = harness.service.submit(command)
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_publication_evidence_mismatch"
    assert tuple(harness.ledger.iter_events()) == ()


def test_stale_expected_version_conflicts_without_append(tmp_path) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    command = publication_command()
    command["expected_stream_version"] = 1
    receipt = harness.service.submit(command)
    assert receipt.status == "conflict"
    assert receipt.reason_code == "stream_version_conflict"
    assert receipt.observed_stream_version == 0
    assert tuple(harness.ledger.iter_events()) == ()


def test_distinct_command_cannot_republish_existing_decision(tmp_path) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    harness.service.submit(publication_command())
    second = publication_command(
        "cmd_01978abc-2012-7000-8000-000000002012"
    )
    second["idempotency_key"] = "release-publication:distinct"
    second["payload"] = {
        **second["payload"],
        "idempotency_key": "release-publication:distinct",
    }
    receipt = harness.service.submit(second)
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_decision_already_published"
    assert len(tuple(harness.ledger.iter_events())) == 1


def test_index_first_receipt_crash_recovers_exactly_one_publication(
    tmp_path,
    monkeypatch,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    original_write = harness.receipts.write
    monkeypatch.setattr(
        harness.receipts,
        "write",
        lambda _receipt: (_ for _ in ()).throw(OSError("receipt crash")),
    )
    with pytest.raises(OSError, match="receipt crash"):
        harness.service.submit(publication_command())
    assert len(tuple(harness.ledger.iter_events())) == 1
    monkeypatch.setattr(harness.receipts, "write", original_write)
    recovered = harness.service.submit(
        publication_command(
            "cmd_01978abc-2013-7000-8000-000000002013"
        )
    )
    assert recovered.status == "accepted"
    assert len(tuple(harness.ledger.iter_events())) == 1


def test_concurrent_exact_publications_serialize_to_one_original_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(
            authority_grant_sha256="a" * 64
        )
    )
    harness.service.release_publication_evidence = evidence_resolver()
    entered = threading.Event()
    release = threading.Event()

    def pause(_temporary):
        entered.set()
        assert release.wait(2)

    monkeypatch.setattr(harness.ledger, "_after_batch_fsync", pause)
    results = []
    errors = []

    def submit(command):
        try:
            results.append(harness.service.submit(command))
        except Exception as exc:  # pragma: no branch - asserted below
            errors.append(exc)

    first = threading.Thread(target=submit, args=(publication_command(),))
    second = threading.Thread(
        target=submit,
        args=(
            publication_command(
                "cmd_01978abc-2014-7000-8000-000000002014"
            ),
        ),
    )
    first.start()
    assert entered.wait(2)
    second.start()
    time.sleep(0.05)
    release.set()
    first.join(2)
    second.join(2)
    assert errors == []
    assert len(results) == 2
    assert results[0] == results[1]
    assert len(tuple(harness.ledger.iter_events())) == 1
