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
    load_selected_grandfather_decision,
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


def _decision(tmp_path: Path, *, missing_prefix_provenance: bool = False):
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
    if missing_prefix_provenance:
        path = harness.ledger._batch_paths()[0]
        event = json.loads(path.read_text(encoding="utf-8"))
        for field in ("command_schema_id", "command_schema_version", "command_schema_sha256"):
            event.pop(field)
        event.pop("event_hash")
        event["event_hash"] = sha256_hex(canonical_bytes(event))
        path.write_bytes(canonical_bytes(event) + b"\n")
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


def _pin_selected_decision(monkeypatch, tmp_path: Path, decision: GrandfatherDecision) -> None:
    decision_path = "selected-grandfather-decision.json"
    (tmp_path / decision_path).write_bytes(canonical_bytes(decision.as_record()) + b"\n")
    authority_manifest = tmp_path / "authority-manifest.yaml"
    authority_manifest.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://tests/wp6-1/06h-current-append-manifest",
                "schema_version": "1.0.0",
                "historical_evidence": {
                    "protocol_activation": decision.as_record()["protocol"],
                    "decision_record": decision_path,
                    "owner_protocol_decision": decision.sha256,
                    "selected_lineage": decision.candidate_lineage,
                },
            }
        )
    )
    monkeypatch.setattr(grandfather_module, "_REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(grandfather_module, "_AUTHORITY_MANIFEST_PATH", authority_manifest)
    monkeypatch.setattr(grandfather_module, "_SELECTED_DECISION_RELATIVE_PATH", decision_path)
    monkeypatch.setattr(grandfather_module, "_SELECTED_CANDIDATE_LINEAGE", decision.candidate_lineage)


def test_public_grandfather_capture_materialize_and_repeat_replay_are_stable(tmp_path, monkeypatch):
    harness, snapshot, decision = _decision(tmp_path)
    _pin_selected_decision(monkeypatch, tmp_path, decision)
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
    )
    second_replay = replay_grandfathered(
        harness.ledger,
        decision,
        schema_registry=harness.schemas,
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


@pytest.mark.parametrize("invalid_bound", [0, -1, True])
def test_public_grandfather_capture_rejects_invalid_bound_before_snapshot(tmp_path, monkeypatch, invalid_bound):
    harness, snapshot, _ = _decision(tmp_path)

    def snapshot_must_not_run():
        raise AssertionError("snapshot called before grandfather bound validation")

    monkeypatch.setattr(harness.ledger, "snapshot", snapshot_must_not_run)

    with pytest.raises(IntegrityError, match="maximum global position must be positive"):
        capture_grandfather_prefix(
            harness.ledger,
            expected_snapshot=snapshot,
            store_identity=STORE_IDENTITY,
            max_global_position=invalid_bound,
            expected_tail_hash=snapshot.event_hash,
        )


def test_public_grandfather_capture_uses_explicit_stable_batch_order(tmp_path, monkeypatch):
    harness, _, _ = _decision(tmp_path)
    harness.service.submit(
        create_task_command(
            "cmd_01978abc-4003-7000-8000-000000004003",
            "grandfather-second-batch",
            "tsk_01978abc-4004-7000-8000-000000004004",
            {"title": "Second prefix batch"},
        )
    )
    snapshot = harness.ledger.snapshot()
    evidence = capture_grandfather_prefix(
        harness.ledger,
        expected_snapshot=snapshot,
        store_identity=STORE_IDENTITY,
        max_global_position=2,
        expected_tail_hash=snapshot.event_hash,
    )
    original_batch_paths = harness.ledger._batch_paths

    monkeypatch.setattr(harness.ledger, "_batch_paths", lambda: list(reversed(original_batch_paths())))

    assert (
        capture_grandfather_prefix(
            harness.ledger,
            expected_snapshot=snapshot,
            store_identity=STORE_IDENTITY,
            max_global_position=2,
            expected_tail_hash=snapshot.event_hash,
        )
        == evidence
    )


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


def test_public_grandfather_materialization_rejects_post_link_destination_swap(tmp_path, monkeypatch):
    harness, snapshot, decision = _decision(tmp_path)
    output = tmp_path / "evidence" / "grandfather-decision.json"
    output.parent.mkdir()
    replacement = b"post-link replacement\n"
    real_link = os.link
    swapped = False

    def link_then_swap(source, destination):
        nonlocal swapped
        real_link(source, destination)
        Path(destination).unlink()
        Path(destination).write_bytes(replacement)
        swapped = True

    monkeypatch.setattr(os, "link", link_then_swap)

    with pytest.raises((ConflictError, IntegrityError), match="published|destination"):
        materialize_grandfather_decision(
            harness.ledger,
            decision,
            output,
            expected_snapshot=snapshot,
        )

    assert swapped
    assert output.read_bytes() == replacement


def test_public_grandfather_replay_admits_exact_prefix_and_later_complete_event(tmp_path, monkeypatch):
    harness, _, decision = _decision(tmp_path)
    _pin_selected_decision(monkeypatch, tmp_path, decision)
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
    )

    assert projection["last_position"] == 2
    assert projection["streams"][later_task]["status"] == "draft"


def test_public_grandfather_replay_admits_exact_missing_triple_within_bound(tmp_path, monkeypatch):
    harness, _, decision = _decision(tmp_path, missing_prefix_provenance=True)
    _pin_selected_decision(monkeypatch, tmp_path, decision)

    projection = replay_grandfathered(
        harness.ledger,
        decision,
        schema_registry=harness.schemas,
    )

    assert decision.evidence.missing_triple_positions == (1,)
    assert projection["last_position"] == 1


def test_public_grandfather_replay_rejects_unlisted_missing_triple_within_bound(tmp_path, monkeypatch):
    harness, _, decision = _decision(tmp_path, missing_prefix_provenance=True)
    unlisted = replace(
        decision,
        evidence=replace(
            decision.evidence,
            missing_triple_positions=(),
            missing_triple_set_sha256=sha256_hex(canonical_bytes([])),
        ),
    )
    _pin_selected_decision(monkeypatch, tmp_path, unlisted)

    with pytest.raises(IntegrityError, match="grandfather prefix evidence mismatch"):
        replay_grandfathered(
            harness.ledger,
            unlisted,
            schema_registry=harness.schemas,
        )


def test_public_grandfather_replay_rejects_missing_provenance_beyond_bound(tmp_path, monkeypatch):
    harness, _, decision = _decision(tmp_path)
    _pin_selected_decision(monkeypatch, tmp_path, decision)
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
        )


def test_public_grandfather_replay_rejects_rewritten_bound_prefix(tmp_path, monkeypatch):
    harness, _, decision = _decision(tmp_path)
    _pin_selected_decision(monkeypatch, tmp_path, decision)
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
def test_public_grandfather_replay_rejects_changed_or_nonempty_decision_pins(tmp_path, monkeypatch, changed_evidence):
    harness, _, decision = _decision(tmp_path)
    _pin_selected_decision(monkeypatch, tmp_path, decision)
    changed = replace(decision, evidence=replace(decision.evidence, **changed_evidence))

    with pytest.raises((IntegrityError, ValueError), match="grandfather|missing-triple"):
        replay_grandfathered(
            harness.ledger,
            changed,
            schema_registry=harness.schemas,
        )


def test_public_grandfather_replay_rejects_changed_decision_attribution(tmp_path, monkeypatch):
    harness, _, decision = _decision(tmp_path)
    _pin_selected_decision(monkeypatch, tmp_path, decision)
    changed = replace(decision, selected_by="Unattributed replacement")

    with pytest.raises(IntegrityError, match="grandfather decision authority mismatch"):
        replay_grandfathered(
            harness.ledger,
            changed,
            schema_registry=harness.schemas,
        )


def test_public_grandfather_replay_rejects_forged_attribution_with_self_digest(tmp_path, monkeypatch):
    harness, _, decision = _decision(tmp_path)
    _pin_selected_decision(monkeypatch, tmp_path, decision)
    forged = replace(
        decision,
        selected_by="Forged selector",
        owner_statement="Forged statement",
        candidate_lineage="4" * 40,
    )

    with pytest.raises(IntegrityError, match="grandfather decision authority mismatch"):
        replay_grandfathered(
            harness.ledger,
            forged,
            schema_registry=harness.schemas,
        )


def test_selected_grandfather_decision_resolves_from_external_repository_pin():
    decision = load_selected_grandfather_decision()

    assert decision.sha256 == "07eac8199ffb48ceea6e0d235f0f2193fac4ebaae4b1e3340e39899e59927c74"
    assert decision.candidate_lineage == CANDIDATE_LINEAGE
