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
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    AUTHORITY_GRANT_ID,
    PROJECT_ID,
    RELEASE_DECISION_ID,
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
    origin_authority_root = tmp_path / "origin-authority"
    origin_authority_root.mkdir()
    bootstrap = authority_bootstrap()
    identity = initialize_authority_control_store(
        [ROOT],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        origin_authority_root=origin_authority_root,
    )
    schemas = runtime_schema_registry(SCHEMAS)
    ledger = EventLedger(control_root, PROJECT_ID, schemas)
    resolver = LedgerAuthorityGrantResolver(
        control_root,
        PROJECT_ID,
        identity,
        schemas,
        approved_witness=identity.witness,
        approved_witness_path=identity.witness_path,
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
    original = service.submit(publish_release_command(COMMAND_ID, authority_hash))
    duplicate = service.submit(publish_release_command(RETRY_ID, authority_hash))
    assert original.status == "accepted"
    assert duplicate == original
    events = tuple(ledger.iter_events())
    publication = [event for event in events if event["event_type"] == "ReleaseGateDecisionPublished"]
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


def test_offline_cli_publish_requires_materialized_canonical_foundation(
    tmp_path,
    capsys,
) -> None:
    control_root = tmp_path / "cli-control"
    origin_authority_root = tmp_path / "origin-authority"
    origin_authority_root.mkdir()
    bootstrap = authority_bootstrap(publication_expires_at="2099-01-01T00:00:00Z")
    identity = initialize_authority_control_store(
        [ROOT],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        origin_authority_root=origin_authority_root,
    )
    config = tmp_path / "control-binding.yaml"
    config.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(ROOT.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str(SCHEMAS.resolve()),
                "store_identity": str(identity),
            }
        )
    )
    source_path = tmp_path / "evaluation-runs.json"
    source_path.write_bytes(canonical_bytes(synthetic_release_decision()))
    output = tmp_path / "receipt.json"
    output.write_bytes(b"pre-existing")

    assert (
        main(
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
                str(output),
            ]
        )
        == 1
    )
    assert "approved control_root has no matching materialized store" in capsys.readouterr().err
    assert output.read_bytes() == b"pre-existing"
    assert len(tuple(EventLedger(control_root, PROJECT_ID, SchemaRegistry(SCHEMAS)).iter_events())) == 2


def test_real_offline_cli_publish_requires_materialized_canonical_foundation(
    tmp_path,
    capsys,
) -> None:
    coverage = ROOT / ".research-system" / "evals" / "p0-coverage.yaml"
    source_path = tmp_path / "real-source.json"
    assert (
        main(
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
        )
        == 0
    )
    capsys.readouterr()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    decision_id = source["release_gate_decision_id"]
    bootstrap = authority_bootstrap(
        publication_target_id=decision_id,
        publication_expires_at="2099-01-01T00:00:00Z",
    )
    control_root = tmp_path / "real-control"
    origin_authority_root = tmp_path / "origin-authority"
    origin_authority_root.mkdir()
    identity = initialize_authority_control_store(
        [ROOT],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        origin_authority_root=origin_authority_root,
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
    assert (
        main(
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
        )
        == 1
    )
    assert "approved control_root has no matching materialized store" in capsys.readouterr().err
    assert not receipt.exists()
    assert len(tuple(EventLedger(control_root, PROJECT_ID, SchemaRegistry(SCHEMAS)).iter_events())) == 2
