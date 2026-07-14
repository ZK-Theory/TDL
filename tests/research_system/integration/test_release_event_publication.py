import json
from datetime import UTC, datetime
from pathlib import Path

from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.command.service import CommandService
from research_system.canonical import canonical_bytes
from research_system.cli import main
from research_system.evals.release_publication import verify_replayed_release
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    AUTHORITY_GRANT_ID,
    ACTORS,
    PROJECT_ID,
    RELEASE_DECISION_ID,
    ROOT_AUTHORITY_GRANT_ID,
    authority_bootstrap,
    publish_release_command,
    synthetic_publication_evidence,
    synthetic_release_decision,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
COMMAND_ID = "cmd_01978abc-3001-7000-8000-000000003001"
RETRY_ID = "cmd_01978abc-3002-7000-8000-000000003002"


def publication_service(tmp_path):
    control_root = tmp_path / "canonical-control"
    bootstrap = authority_bootstrap()
    identity = initialize_authority_control_store(
        [ROOT],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )
    schemas = SchemaRegistry(SCHEMAS)
    ledger = EventLedger(control_root, PROJECT_ID, schemas)
    resolver = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        identity,
        schemas,
    )
    service = CommandService(
        control_root,
        ledger,
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        release_publication_evidence=synthetic_publication_evidence(identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    return service, ledger, schemas, bootstrap


def test_canonical_resolver_command_ledger_replay_and_release_are_bound(
    tmp_path,
) -> None:
    service, ledger, schemas, bootstrap = publication_service(tmp_path)
    authority_hash = bootstrap["publication_grant_sha256"]
    original = service.submit(
        publish_release_command(COMMAND_ID, authority_hash)
    )
    duplicate = service.submit(
        publish_release_command(RETRY_ID, authority_hash)
    )
    assert original.status == "accepted"
    assert duplicate == original
    events = tuple(ledger.iter_events())
    publication = [
        event
        for event in events
        if event["event_type"] == "ReleaseGateDecisionPublished"
    ]
    assert len(publication) == 1
    event = publication[0]
    assert event["stream_id"] == RELEASE_DECISION_ID
    assert event["authority_grant_id"] == AUTHORITY_GRANT_ID
    assert event["payload"]["release_decision"]["canonical_event_ref"] == event["event_id"]
    projection = replay(events, schema_registry=schemas)
    source = synthetic_release_decision()
    published = dict(source)
    published["canonical_event_ref"] = event["event_id"]
    resolved = verify_replayed_release(
        published,
        source,
        projection,
        PROJECT_ID,
        service.release_publication_evidence,
        schemas,
    )
    assert resolved["event_id"] == event["event_id"]
    assert resolved["gate5_authorized"] is False
    assert resolved["candidate_status"] == "blocked"


def test_offline_cli_publish_retry_replay_and_release(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    control_root = tmp_path / "cli-control"
    bootstrap = authority_bootstrap(
        publication_expires_at="2099-01-01T00:00:00Z"
    )
    identity = initialize_authority_control_store(
        [ROOT],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )
    config = tmp_path / "control-binding.yaml"
    config.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(ROOT.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str(SCHEMAS.resolve()),
                "store_identity": identity,
            }
        )
    )
    source = synthetic_release_decision()
    evaluation_runs = tmp_path / "evaluation-runs.json"
    evaluation_runs.write_bytes(canonical_bytes(source))
    first_output = tmp_path / "receipt-1.json"
    command = [
        "eval",
        "publish-release",
        "--config",
        str(config),
        "--actor-id",
        "act_01978abc-1002-7000-8000-000000001002",
        "--authority-grant-id",
        AUTHORITY_GRANT_ID,
        "--evaluation-runs",
        str(evaluation_runs),
        "--output",
        str(first_output),
    ]
    first_output.write_bytes(b"pre-existing")
    assert main(command) == 1
    capsys.readouterr()
    assert len(tuple(EventLedger(control_root, PROJECT_ID, SchemaRegistry(SCHEMAS)).iter_events())) == 2
    first_output.unlink()

    def interrupt(_temporary):
        raise OSError("injected output interruption")

    monkeypatch.setattr(
        "research_system.cli._after_receipt_output_fsync", interrupt
    )
    try:
        main(command)
    except OSError as exc:
        assert str(exc) == "injected output interruption"
    else:  # pragma: no cover - fail closed if CLI starts swallowing OSError
        raise AssertionError("injected output interruption was not raised")
    assert not first_output.exists()
    monkeypatch.setattr(
        "research_system.cli._after_receipt_output_fsync", lambda _path: None
    )

    race_output = tmp_path / "receipt-race.json"
    command[-1] = str(race_output)

    def create_race(_temporary):
        race_output.write_bytes(b"racing writer")

    monkeypatch.setattr(
        "research_system.cli._after_receipt_output_fsync", create_race
    )
    assert main(command) == 1
    capsys.readouterr()
    assert race_output.read_bytes() == b"racing writer"
    monkeypatch.setattr(
        "research_system.cli._after_receipt_output_fsync", lambda _path: None
    )
    command[-1] = str(first_output)
    assert main(command) == 0
    capsys.readouterr()
    second_output = tmp_path / "receipt-2.json"
    command[-1] = str(second_output)
    assert main(command) == 0
    capsys.readouterr()
    assert json.loads(first_output.read_text(encoding="utf-8")) == json.loads(
        second_output.read_text(encoding="utf-8")
    )
    changed_source = dict(source)
    changed_source["decided_at"] = "2026-07-14T04:00:00+00:00"
    changed_source_path = tmp_path / "evaluation-runs-changed.json"
    changed_source_path.write_bytes(canonical_bytes(changed_source))
    changed_output = tmp_path / "receipt-changed.json"
    command[-3] = str(changed_source_path)
    command[-1] = str(changed_output)
    assert main(command) == 0
    capsys.readouterr()
    changed_receipt = json.loads(changed_output.read_text(encoding="utf-8"))
    assert changed_receipt["status"] == "conflict"
    assert changed_receipt["reason_code"] == "idempotency_conflict"
    assert len(
        [
            event
            for event in EventLedger(
                control_root, PROJECT_ID, SchemaRegistry(SCHEMAS)
            ).iter_events()
            if event["event_type"] == "ReleaseGateDecisionPublished"
        ]
    ) == 1
    command[-3] = str(evaluation_runs)
    schemas = SchemaRegistry(SCHEMAS)
    revocation_service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, schemas),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=LedgerAuthorityGrantResolver(
            control_root,
            PROJECT_ID,
            identity,
            schemas,
        ),
        clock=lambda: datetime(2026, 7, 14, 12, tzinfo=UTC),
    )
    revoked = revocation_service.submit(
        {
            "command_id": "cmd_01978abc-3090-7000-8000-000000003090",
            "command_type": "RevokeAuthorityGrant",
            "schema_id": "ars://core/command",
            "schema_version": "1.0.0",
            "submitted_at": "2026-07-14T12:00:00Z",
            "actor_id": ACTORS["actor-a"],
            "on_behalf_of_actor_id": None,
            "authority_grant_id": ROOT_AUTHORITY_GRANT_ID,
            "target_stream_id": AUTHORITY_GRANT_ID,
            "expected_stream_version": 1,
            "idempotency_key": "revoke-after-release-publication",
            "correlation_id": "release-publication-revocation",
            "causation_id": None,
            "reason": "prove historical publication remains valid",
            "evidence_refs": [],
            "payload": {
                "project_id": PROJECT_ID,
                "target_grant_id": AUTHORITY_GRANT_ID,
                "target_grant_sha256": bootstrap["publication_grant_sha256"],
                "authority_grant_sha256": bootstrap["root_grant_sha256"],
                "reason": "prove historical publication remains valid",
            },
        }
    )
    assert revoked.status == "accepted"
    post_revocation_output = tmp_path / "receipt-post-revocation.json"
    command[-1] = str(post_revocation_output)
    assert main(command) == 0
    capsys.readouterr()
    assert json.loads(post_revocation_output.read_text(encoding="utf-8")) == (
        json.loads(first_output.read_text(encoding="utf-8"))
    )
    assert main(["replay", "verify", "--control-root", str(control_root)]) == 0
    replayed = json.loads(capsys.readouterr().out)
    assert replayed["release_decisions"][RELEASE_DECISION_ID][
        "gate5_authorized"
    ] is False
    assert main(
        [
            "eval",
            "release",
            "--config",
            str(config),
            "--evaluation-runs",
            str(evaluation_runs),
        ]
    ) == 1
    capsys.readouterr()
    published = dict(source)
    published["canonical_event_ref"] = replayed["release_decisions"][
        RELEASE_DECISION_ID
    ]["event_id"]
    evaluation_runs.write_bytes(canonical_bytes(published))
    assert main(
        [
            "eval",
            "release",
            "--config",
            str(config),
            "--evaluation-runs",
            str(evaluation_runs),
        ]
    ) == 0
    released = json.loads(capsys.readouterr().out)
    assert released["candidate_status"] == "blocked"
    assert released["gate5_authorized"] is False


def test_real_offline_cli_rederivation_reaches_published_release(
    tmp_path,
    capsys,
) -> None:
    coverage = ROOT / ".research-system" / "evals" / "p0-coverage.yaml"
    source_path = tmp_path / "real-source.json"
    assert main(
        [
            "eval",
            "run",
            "--coverage",
            str(coverage),
            "--transport",
            "fake",
            "--output",
            str(source_path),
        ]
    ) == 0
    capsys.readouterr()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    decision_id = source["release_gate_decision_id"]
    bootstrap = authority_bootstrap(
        publication_target_id=decision_id,
        publication_expires_at="2099-01-01T00:00:00Z",
    )
    control_root = tmp_path / "real-control"
    identity = initialize_authority_control_store(
        [ROOT],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )
    config = tmp_path / "real-binding.json"
    config.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(ROOT.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str(SCHEMAS.resolve()),
                "store_identity": identity,
            }
        )
    )
    receipt = tmp_path / "real-receipt.json"
    assert main(
        [
            "eval",
            "publish-release",
            "--config",
            str(config),
            "--actor-id",
            "act_01978abc-1002-7000-8000-000000001002",
            "--authority-grant-id",
            AUTHORITY_GRANT_ID,
            "--evaluation-runs",
            str(source_path),
            "--output",
            str(receipt),
        ]
    ) == 0
    capsys.readouterr()
    schemas = SchemaRegistry(SCHEMAS)
    projection = replay(
        EventLedger(control_root, PROJECT_ID, schemas).iter_events(),
        schema_registry=schemas,
    )
    published = dict(source)
    published["canonical_event_ref"] = projection["release_decisions"][
        decision_id
    ]["event_id"]
    published_path = tmp_path / "real-published.json"
    published_path.write_bytes(canonical_bytes(published))
    assert main(
        [
            "eval",
            "release",
            "--config",
            str(config),
            "--evaluation-runs",
            str(published_path),
        ]
    ) == 0
    released = json.loads(capsys.readouterr().out)
    assert released == {
        "candidate_status": "blocked",
        "canonical_event_ref": published["canonical_event_ref"],
        "decision": "blocked",
        "gate5_authorized": False,
    }
