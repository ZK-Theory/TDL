from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError, IntegrityError
from research_system.projection.grandfather import (
    GrandfatherDecision,
    capture_grandfather_prefix,
    load_grandfather_decision,
    materialize_grandfather_decision,
    replay_grandfathered,
)
import research_system.projection.grandfather as grandfather_module
from tests.research_system.factories import PROJECT_ID, control_plane, create_task_command


STORE_IDENTITY = "2" * 64
OWNER_STATEMENT = (
    "SELECT G-RM-8 GRANDFATHER for candidate lineage 3c75d3d; "
    "authorize bounded construction and required evidence capture."
)
CANDIDATE_LINEAGE = "3c75d3d102d8fe14746b19662005e88c4b776ffa"


def _write_store_identity(control_root: Path, *, store_identity: str = STORE_IDENTITY) -> None:
    manifest = {
        "schema_id": "ars://core/store-identity",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "store_identity": store_identity,
        "control_root": str(control_root.resolve()),
        "code_roots": [],
        "endpoint_scheme": "local-cli",
    }
    manifest["manifest_hash"] = sha256_hex(canonical_bytes(manifest))
    path = control_root / "manifests" / "store-identity.json"
    path.parent.mkdir()
    path.write_bytes(canonical_bytes(manifest))


def _decision(tmp_path: Path):
    harness = control_plane(tmp_path)
    _write_store_identity(harness.ledger.control_root)
    harness.service.submit(
        create_task_command(
            "cmd_01978abc-4001-7000-8000-000000004001",
            "grandfather-first",
            "tsk_01978abc-4002-7000-8000-000000004002",
            {"title": "Frozen prefix"},
        )
    )
    snapshot = harness.ledger.snapshot()
    evidence = capture_grandfather_prefix(
        harness.ledger,
        expected_snapshot=snapshot,
        store_identity=STORE_IDENTITY,
        max_global_position=1,
        expected_tail_hash=snapshot.event_hash,
    )
    decision = GrandfatherDecision.select(
        selected_by="Stephen Dorman",
        selected_at="2026-08-09",
        owner_statement=OWNER_STATEMENT,
        candidate_lineage=CANDIDATE_LINEAGE,
        evidence=evidence,
    )
    return harness, snapshot, decision


def test_public_grandfather_capture_materialize_and_repeat_replay_are_stable(tmp_path):
    harness, snapshot, decision = _decision(tmp_path)
    output = tmp_path / "evidence" / "grandfather-decision.json"
    output.parent.mkdir()

    first_hash = materialize_grandfather_decision(
        harness.ledger,
        decision,
        output,
        expected_snapshot=snapshot,
    )
    second_hash = materialize_grandfather_decision(
        harness.ledger,
        decision,
        output,
        expected_snapshot=snapshot,
    )
    first_replay = replay_grandfathered(
        harness.ledger,
        decision,
        schema_registry=harness.schemas,
        expected_decision_sha256=decision.sha256,
    )
    second_replay = replay_grandfathered(
        harness.ledger,
        decision,
        schema_registry=harness.schemas,
        expected_decision_sha256=decision.sha256,
    )

    assert decision.evidence.missing_triple_positions == ()
    assert first_hash == second_hash == decision.sha256
    assert load_grandfather_decision(output) == decision
    assert first_replay == second_replay


def test_public_grandfather_materialization_rejects_a_changed_expected_tail(tmp_path):
    harness, snapshot, decision = _decision(tmp_path)
    output = tmp_path / "evidence" / "grandfather-decision.json"
    output.parent.mkdir()
    harness.service.submit(
        create_task_command(
            "cmd_01978abc-4003-7000-8000-000000004003",
            "grandfather-second",
            "tsk_01978abc-4004-7000-8000-000000004004",
            {"title": "Concurrent append"},
        )
    )

    with pytest.raises(ConflictError, match="expected ledger tail changed"):
        materialize_grandfather_decision(
            harness.ledger,
            decision,
            output,
            expected_snapshot=snapshot,
        )

    assert not output.exists()


def test_public_grandfather_capture_rejects_same_size_restored_mtime_prefix_aba(tmp_path, monkeypatch):
    harness, snapshot, _ = _decision(tmp_path)
    batch_path = harness.ledger._batch_paths()[0]
    original_raw = batch_path.read_bytes()
    original_stat = batch_path.stat()
    rewritten_raw = original_raw.replace(b"Frozen prefix", b"Mutant prefix")
    assert rewritten_raw != original_raw
    assert len(rewritten_raw) == len(original_raw)
    real_read_bytes = Path.read_bytes
    rewritten = False

    def rewrite_on_digest_read(path: Path) -> bytes:
        nonlocal rewritten
        if path == batch_path and not rewritten:
            batch_path.write_bytes(rewritten_raw)
            os.utime(batch_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            rewritten = True
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", rewrite_on_digest_read)

    with pytest.raises((ConflictError, IntegrityError), match="grandfather prefix"):
        capture_grandfather_prefix(
            harness.ledger,
            expected_snapshot=snapshot,
            store_identity=STORE_IDENTITY,
            max_global_position=1,
            expected_tail_hash=snapshot.event_hash,
        )


def test_public_grandfather_materialization_never_overwrites_competing_decision(tmp_path, monkeypatch):
    harness, snapshot, decision = _decision(tmp_path)
    output = tmp_path / "evidence" / "grandfather-decision.json"
    output.parent.mkdir()
    competing = b"competing decision\n"
    real_verify = grandfather_module._verify_decision
    planted = False

    def plant_competing_decision(ledger, candidate):
        nonlocal planted
        result = real_verify(ledger, candidate)
        if not planted:
            output.write_bytes(competing)
            planted = True
        return result

    monkeypatch.setattr(grandfather_module, "_verify_decision", plant_competing_decision)

    with pytest.raises(ConflictError, match="destination conflicts"):
        materialize_grandfather_decision(
            harness.ledger,
            decision,
            output,
            expected_snapshot=snapshot,
        )

    assert output.read_bytes() == competing
    assert list(output.parent.glob(f".{output.name}.*.tmp")) == []


def test_public_grandfather_replay_admits_exact_prefix_and_later_complete_event(tmp_path):
    harness, _, decision = _decision(tmp_path)
    later_task = "tsk_01978abc-4004-7000-8000-000000004004"
    harness.service.submit(
        create_task_command(
            "cmd_01978abc-4003-7000-8000-000000004003",
            "grandfather-later",
            later_task,
            {"title": "Later complete event"},
        )
    )

    projection = replay_grandfathered(
        harness.ledger,
        decision,
        schema_registry=harness.schemas,
        expected_decision_sha256=decision.sha256,
    )

    assert projection["last_position"] == 2
    assert projection["streams"][later_task]["status"] == "draft"


def test_public_grandfather_replay_rejects_missing_provenance_beyond_bound(tmp_path):
    harness, _, decision = _decision(tmp_path)
    harness.service.submit(
        create_task_command(
            "cmd_01978abc-4003-7000-8000-000000004003",
            "grandfather-malformed",
            "tsk_01978abc-4004-7000-8000-000000004004",
            {"title": "Later malformed event"},
        )
    )
    path = harness.ledger._batch_paths()[-1]
    event = json.loads(path.read_text(encoding="utf-8"))
    for field in ("command_schema_id", "command_schema_version", "command_schema_sha256"):
        event.pop(field)
    event.pop("event_hash")
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    path.write_bytes(canonical_bytes(event) + b"\n")

    with pytest.raises(IntegrityError, match="missing command schema identity at 2"):
        replay_grandfathered(
            harness.ledger,
            decision,
            schema_registry=harness.schemas,
            expected_decision_sha256=decision.sha256,
        )


def test_public_grandfather_replay_rejects_rewritten_bound_prefix(tmp_path):
    harness, _, decision = _decision(tmp_path)
    path = harness.ledger._batch_paths()[0]
    event = json.loads(path.read_text(encoding="utf-8"))
    event["payload"]["title"] = "Rewritten prefix"
    event.pop("event_hash")
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    path.write_bytes(canonical_bytes(event) + b"\n")

    with pytest.raises(IntegrityError, match="grandfather prefix evidence mismatch"):
        replay_grandfathered(
            harness.ledger,
            decision,
            schema_registry=harness.schemas,
            expected_decision_sha256=decision.sha256,
        )


@pytest.mark.parametrize(
    "changed_evidence",
    (
        {"store_identity": "3" * 64},
        {"ledger_prefix_sha256": "3" * 64},
        {"max_global_position": 2},
        {"historical_event_set_sha256": "3" * 64},
        {"missing_triple_set_sha256": "3" * 64},
        {"missing_triple_positions": (1,)},
    ),
)
def test_public_grandfather_replay_rejects_changed_or_nonempty_decision_pins(tmp_path, changed_evidence):
    harness, _, decision = _decision(tmp_path)
    changed = replace(decision, evidence=replace(decision.evidence, **changed_evidence))

    with pytest.raises((IntegrityError, ValueError), match="grandfather|missing-triple"):
        replay_grandfathered(
            harness.ledger,
            changed,
            schema_registry=harness.schemas,
            expected_decision_sha256=changed.sha256,
        )


def test_public_grandfather_replay_rejects_changed_decision_attribution(tmp_path):
    harness, _, decision = _decision(tmp_path)
    changed = replace(decision, selected_by="Unattributed replacement")

    with pytest.raises(IntegrityError, match="grandfather decision identity mismatch"):
        replay_grandfathered(
            harness.ledger,
            changed,
            schema_registry=harness.schemas,
            expected_decision_sha256=decision.sha256,
        )
