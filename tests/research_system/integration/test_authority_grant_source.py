from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import threading

import pytest

from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.cli import main
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import REPO_ROOT


PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
ACTOR_ID = "act_01978abc-1002-7000-8000-000000001002"
ROOT_ID = "agr_01978abc-1004-7000-8000-000000001004"
PUBLICATION_ID = "agr_01978abc-1001-7000-8000-000000001001"
DECISION_ID = "rgd_01978abc-1003-7000-8000-000000001003"
CMD_REVOKE = "cmd_01978abc-1005-7000-8000-000000001005"
CMD_RETRY = "cmd_01978abc-1006-7000-8000-000000001006"


def _grant(
    grant_id: str,
    command: str,
    subject_kind: str,
    subject_id: str,
    *,
    expires_at: str | None,
) -> dict[str, object]:
    return {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": grant_id,
        "actor_id": ACTOR_ID,
        "allowed_command_types": [command],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": subject_kind, "id": subject_id},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": expires_at,
        "delegable": False,
        "revoked": False,
    }


def _bootstrap() -> dict[str, object]:
    root = _grant(
        ROOT_ID,
        "RevokeAuthorityGrant",
        "authority_grant",
        PUBLICATION_ID,
        expires_at=None,
    )
    publication = _grant(
        PUBLICATION_ID,
        "PublishReleaseGateDecision",
        "release_gate_decision",
        DECISION_ID,
        expires_at="2026-07-13T00:00:00Z",
    )
    return {
        "schema_id": "ars://core/authority-bootstrap-manifest",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "owner_actor_id": ACTOR_ID,
        "root_grant": root,
        "root_grant_sha256": sha256_hex(canonical_bytes(root)),
        "publication_grant": publication,
        "publication_grant_sha256": sha256_hex(canonical_bytes(publication)),
        "publication_target_id": DECISION_ID,
    }


def _initialized(tmp_path):
    code_root = tmp_path / "repo"
    code_root.mkdir()
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()
    approved = authority_bootstrap_sha256(bootstrap)
    identity = initialize_authority_control_store(
        [code_root], control_root, PROJECT_ID, bootstrap, approved
    )
    return control_root, bootstrap, identity


def test_genesis_is_atomic_replay_derived_and_exact_retry_is_read_only(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    before = sorted(
        (path.relative_to(control_root).as_posix(), path.read_bytes())
        for path in control_root.rglob("*")
        if path.is_file()
    )
    assert initialize_authority_control_store(
        [tmp_path / "repo"],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    ) == identity
    assert before == sorted(
        (path.relative_to(control_root).as_posix(), path.read_bytes())
        for path in control_root.rglob("*")
        if path.is_file()
    )
    events = tuple(EventLedger(control_root, PROJECT_ID).iter_events())
    assert [event["event_type"] for event in events] == [
        "AuthorityRootInitialized",
        "AuthorityGrantActivated",
    ]
    assert [event["transaction_index"] for event in events] == [1, 2]
    state = replay(events)
    assert state["authority_grants"][PUBLICATION_ID]["status"] == "active"


def test_changed_retry_legacy_store_and_inert_object_fail_closed(tmp_path) -> None:
    control_root, bootstrap, _ = _initialized(tmp_path)
    changed = deepcopy(bootstrap)
    changed["publication_grant"]["expires_at"] = "2026-07-14T00:00:00Z"
    changed["publication_grant_sha256"] = sha256_hex(
        canonical_bytes(changed["publication_grant"])
    )
    with pytest.raises(ConflictError, match="bootstrap"):
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            changed,
            authority_bootstrap_sha256(changed),
        )

    inert_root = tmp_path / "inert"
    inert_root.mkdir()
    ObjectStore(inert_root).write(
        "authority_grant", PUBLICATION_ID, 1, bootstrap["publication_grant"]
    )
    with pytest.raises(ArsError, match="authority_bootstrap_required"):
        LedgerAuthorityGrantResolver(
            inert_root, PROJECT_ID, "0" * 64
        ).resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 12, 12, tzinfo=UTC),
        )


def test_resolver_enforces_hash_actor_command_project_target_time_and_tamper(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    resolver = LedgerAuthorityGrantResolver(control_root, PROJECT_ID, identity)
    result = resolver.resolve(
        PUBLICATION_ID,
        ACTOR_ID,
        "PublishReleaseGateDecision",
        PROJECT_ID,
        "release_gate_decision",
        DECISION_ID,
        datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert result.authority_grant_sha256 == bootstrap["publication_grant_sha256"]
    for changed in [
        ("act_01978abc-1008-7000-8000-000000001008", "PublishReleaseGateDecision", PROJECT_ID, "release_gate_decision", DECISION_ID),
        (ACTOR_ID, "RevokeAuthorityGrant", PROJECT_ID, "release_gate_decision", DECISION_ID),
        (ACTOR_ID, "PublishReleaseGateDecision", "prj_01978abc-1009-7000-8000-000000001009", "release_gate_decision", DECISION_ID),
        (ACTOR_ID, "PublishReleaseGateDecision", PROJECT_ID, "release_gate_decision", "rgd_01978abc-1007-7000-8000-000000001007"),
    ]:
        with pytest.raises(ArsError):
            resolver.resolve(PUBLICATION_ID, *changed, datetime(2026, 7, 12, 12, tzinfo=UTC))
    with pytest.raises(ArsError, match="effective"):
        resolver.resolve(PUBLICATION_ID, ACTOR_ID, "PublishReleaseGateDecision", PROJECT_ID, "release_gate_decision", DECISION_ID, datetime(2026, 7, 11, tzinfo=UTC))
    with pytest.raises(ArsError, match="expired"):
        resolver.resolve(PUBLICATION_ID, ACTOR_ID, "PublishReleaseGateDecision", PROJECT_ID, "release_gate_decision", DECISION_ID, datetime(2026, 7, 13, tzinfo=UTC))

    grant_path = next((control_root / "objects" / "authority_grant" / PUBLICATION_ID).glob("*.json"))
    grant_path.write_bytes(canonical_bytes({**bootstrap["publication_grant"], "risk_ceiling": "R3"}))
    with pytest.raises(IntegrityError, match="object"):
        resolver.resolve(PUBLICATION_ID, ACTOR_ID, "PublishReleaseGateDecision", PROJECT_ID, "release_gate_decision", DECISION_ID, datetime(2026, 7, 12, 12, tzinfo=UTC))


def _revoke_command(command_id: str) -> dict[str, object]:
    bootstrap = _bootstrap()
    return {
        "command_id": command_id,
        "command_type": "RevokeAuthorityGrant",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": PUBLICATION_ID,
        "expected_stream_version": 1,
        "idempotency_key": "revoke-publication",
        "correlation_id": "synthetic-authority-test",
        "causation_id": None,
        "reason": "synthetic revocation",
        "evidence_refs": [],
        "payload": {
            "project_id": PROJECT_ID,
            "target_grant_id": PUBLICATION_ID,
            "target_grant_sha256": bootstrap["publication_grant_sha256"],
            "authority_grant_sha256": bootstrap["root_grant_sha256"],
            "reason": "synthetic revocation",
        },
    }


def test_revoke_is_locked_monotonic_and_exact_retry_survives_restart(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    resolver = LedgerAuthorityGrantResolver(control_root, PROJECT_ID, identity)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    original_bytes = next((control_root / "objects" / "authority_grant" / PUBLICATION_ID).glob("*.json")).read_bytes()
    original = service.submit(_revoke_command(CMD_REVOKE))
    assert original.status == "accepted"
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=LedgerAuthorityGrantResolver(
            control_root, PROJECT_ID, identity
        ),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    retry = restarted.submit(_revoke_command(CMD_RETRY))
    assert retry == original
    assert len(list((control_root / "receipts" / "idempotency").glob("*.json"))) == 1
    assert next((control_root / "objects" / "authority_grant" / PUBLICATION_ID).glob("*.json")).read_bytes() == original_bytes
    with pytest.raises(ArsError, match="revoked"):
        resolver.resolve(PUBLICATION_ID, ACTOR_ID, "PublishReleaseGateDecision", PROJECT_ID, "release_gate_decision", DECISION_ID, datetime(2026, 7, 12, 12, tzinfo=UTC))
    assert replay(EventLedger(control_root, PROJECT_ID).iter_events())["authority_grants"][PUBLICATION_ID]["revocation_event_id"]


def test_rejected_exact_retry_is_returned_before_current_authority_recheck(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    resolver = LedgerAuthorityGrantResolver(control_root, PROJECT_ID, identity)
    rejected_service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 11, tzinfo=UTC),
    )
    original = rejected_service.submit(_revoke_command(CMD_REVOKE))
    assert original.status == "rejected"
    assert original.reason_code == "authority_revocation_unauthorized"

    current_service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert current_service.submit(_revoke_command(CMD_RETRY)) == original
    assert len(tuple(EventLedger(control_root, PROJECT_ID).iter_events())) == 2


def test_cli_store_init_requires_and_publishes_approved_authority_bootstrap(
    tmp_path, monkeypatch, capsys
) -> None:
    code_root = tmp_path / "repo"
    code_root.mkdir()
    bootstrap = _bootstrap()
    bootstrap_path = tmp_path / "authority-bootstrap.json"
    bootstrap_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-input",
                "schema_version": "1.0.0",
                "approved_bootstrap_sha256": authority_bootstrap_sha256(bootstrap),
                "manifest": bootstrap,
            }
        )
    )
    monkeypatch.setattr(
        "research_system.cli.subprocess.run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 0, "stdout": f"worktree {code_root.resolve()}\n", "stderr": ""}
        )(),
    )
    control_root = tmp_path / "control"
    assert main(
        [
            "store", "init",
            "--code-root", str(code_root),
            "--control-root", str(control_root),
            "--project-id", PROJECT_ID,
            "--authority-bootstrap", str(bootstrap_path),
        ]
    ) == 0
    output = __import__("json").loads(capsys.readouterr().out)
    assert output["bootstrap_manifest_sha256"] == authority_bootstrap_sha256(bootstrap)
    assert output["store_identity"]


def test_pre_rename_crash_leaves_no_visible_store_and_exact_retry_recovers(
    tmp_path, monkeypatch
) -> None:
    code_root = tmp_path / "repo"
    code_root.mkdir()
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()
    approved = authority_bootstrap_sha256(bootstrap)
    real_rename = __import__("os").rename
    monkeypatch.setattr(
        "research_system.authority.os.rename",
        lambda *args: (_ for _ in ()).throw(OSError("pre-rename crash")),
    )
    with pytest.raises(OSError, match="pre-rename crash"):
        initialize_authority_control_store(
            [code_root], control_root, PROJECT_ID, bootstrap, approved
        )
    assert not control_root.exists()
    assert list(tmp_path.glob(".control.authority-stage-*"))
    monkeypatch.setattr("research_system.authority.os.rename", real_rename)
    identity = initialize_authority_control_store(
        [code_root], control_root, PROJECT_ID, bootstrap, approved
    )
    assert LedgerAuthorityGrantResolver(control_root, PROJECT_ID, identity)


def test_competing_initializers_converge_on_one_complete_identity(tmp_path) -> None:
    code_root = tmp_path / "repo"
    code_root.mkdir()
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()
    approved = authority_bootstrap_sha256(bootstrap)
    barrier = threading.Barrier(2)
    identities: list[str] = []
    errors: list[BaseException] = []

    def initialize() -> None:
        try:
            barrier.wait()
            identities.append(
                initialize_authority_control_store(
                    [code_root], control_root, PROJECT_ID, bootstrap, approved
                )
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    workers = [threading.Thread(target=initialize) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert errors == []
    assert len(identities) == 2
    assert identities[0] == identities[1]
    assert len(tuple(EventLedger(control_root, PROJECT_ID).iter_events())) == 2


def test_governed_authority_hook_rechecks_under_same_writer_lock_as_revoke(
    tmp_path
) -> None:
    control_root, _, identity = _initialized(tmp_path)
    resolver = LedgerAuthorityGrantResolver(control_root, PROJECT_ID, identity)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    entered = threading.Event()
    release = threading.Event()

    def governed_operation() -> None:
        service.with_locked_authority(
            authority_grant_id=PUBLICATION_ID,
            actor_id=ACTOR_ID,
            command_type="PublishReleaseGateDecision",
            project_id=PROJECT_ID,
            subject_kind="release_gate_decision",
            subject_id=DECISION_ID,
            callback=lambda result: (
                entered.set(),
                release.wait(2),
                result.authority_grant_sha256,
            )[-1],
        )

    worker = threading.Thread(target=governed_operation)
    worker.start()
    assert entered.wait(1)
    with pytest.raises(ConflictError, match="writer lock exists"):
        service.submit(_revoke_command(CMD_REVOKE))
    release.set()
    worker.join()
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    with pytest.raises(ArsError, match="revoked"):
        service.with_locked_authority(
            authority_grant_id=PUBLICATION_ID,
            actor_id=ACTOR_ID,
            command_type="PublishReleaseGateDecision",
            project_id=PROJECT_ID,
            subject_kind="release_gate_decision",
            subject_id=DECISION_ID,
            callback=lambda result: result,
        )
