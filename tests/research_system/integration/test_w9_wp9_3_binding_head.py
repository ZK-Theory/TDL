# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §9.1; P-081 item 3)
# Purpose: the binding advance's checked-head compare, through the service and through `ars store advance-binding`.
"""The advance compares a checked ledger head under its writer lock (WP9.3 note §9.1, §17 "Pin release").

The fixture is the existing v1.2 reviewed-divergence advance on a scratch store and scratch Git repositories under
``tmp_path`` (``test_store_binding_service``). The checked head travels beside the intent, never inside it, so the
accepted intent and command schemas do not change.
"""

from __future__ import annotations

import functools
import json
from copy import deepcopy
from pathlib import Path

import pytest

from research_system import cli
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConfigurationError, ConflictError
from research_system.ids import new_id
from research_system.store.binding_service import ADVANCE_INTENT_SCHEMA_ID, StoreBindingService
from tests.research_system.integration.test_store_binding_service import _NOW, _reviewed_divergence_intent

MOVED = "binding advance refused: the ledger head moved since the checked head"


def _head(service: StoreBindingService) -> tuple[int, str]:
    snapshot = service.ledger.snapshot()
    return snapshot.global_position, snapshot.event_hash


def _store_state(control: Path) -> dict[str, bytes | None]:
    return {
        str(path.relative_to(control)): path.read_bytes() if path.is_file() else None
        for path in sorted(control.rglob("*"))
        if "receipts" not in path.parts
    }


def _another_writer(service: StoreBindingService) -> None:
    """Append one event as another writer would, so the head moves (a raw, re-hashed copy of the last event)."""
    events = list(service.ledger.iter_events())
    last = deepcopy(events[-1])
    event = {
        **last,
        "event_id": new_id("event"),
        "transaction_id": new_id("event_batch"),
        "global_position": last["global_position"] + 1,
        "stream_version": last["stream_version"] + 1,
        "command_id": "another-writer",
        "idempotency_key": "another-writer",
        "previous_event_hash": last["event_hash"],
    }
    event.pop("event_hash")
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    folder = next(service.control_root.glob(f"events/{service.project_id}/*/*"))
    (folder / f"{event['global_position']:020d}-{event['transaction_id']}.jsonl").write_bytes(
        canonical_bytes(event) + b"\n"
    )


def _prepared(tmp_path: Path):
    service, intent, reviewed = _reviewed_divergence_intent(tmp_path)
    # The service builds its ledger inside advance(); bind it once so the head can be read before.
    from research_system.schema_registry import runtime_schema_registry
    from research_system.store.ledger import EventLedger

    service.ledger = EventLedger(
        service.control_root,
        service.project_id,
        runtime_schema_registry(intent.intended_schema_root),
        store_identity=service.store_identity,
    )
    return service, intent, reviewed


def test_an_advance_given_the_checked_head_succeeds_one_position_after_it(tmp_path: Path) -> None:
    service, intent, _ = _prepared(tmp_path)
    head = _head(service)
    result = service.advance(intent, expected_ledger_head=head)
    assert result["status"] == "advanced"
    events = list(service.ledger.iter_events())
    assert events[-1]["event_type"] == "StoreBindingAdvanced"
    assert events[-1]["global_position"] == head[0] + 1


def test_an_advance_whose_head_moved_refuses_before_its_marker_with_no_effect(tmp_path: Path) -> None:
    service, intent, _ = _prepared(tmp_path)
    head = _head(service)
    _another_writer(service)
    before = _store_state(service.control_root)
    with pytest.raises(ConflictError, match=MOVED):
        service.advance(intent, expected_ledger_head=head)
    assert _store_state(service.control_root) == before
    assert not (service.control_root / "runtime" / ".binding-advance-transaction.json").exists()


def test_a_resumed_advance_completes_after_a_crash_that_followed_its_own_event(tmp_path: Path) -> None:
    service, intent, _ = _prepared(tmp_path)
    head = _head(service)

    def crash(phase: str) -> None:
        if phase == "receipt":
            service.phase_hook = None
            raise OSError("simulated interruption after the event")

    service.phase_hook = crash
    with pytest.raises(OSError, match="simulated interruption after the event"):
        service.advance(intent, expected_ledger_head=head)
    assert _head(service)[0] == head[0] + 1
    assert service.advance(intent, expected_ledger_head=head)["status"] == "advanced"


def test_a_resumed_advance_refuses_after_another_writers_append(tmp_path: Path) -> None:
    service, intent, _ = _prepared(tmp_path)
    head = _head(service)

    def crash(phase: str) -> None:
        if phase == "marker":
            service.phase_hook = None
            raise OSError("simulated interruption after the marker")

    service.phase_hook = crash
    with pytest.raises(OSError, match="simulated interruption after the marker"):
        service.advance(intent, expected_ledger_head=head)
    _another_writer(service)
    with pytest.raises(ConflictError, match=MOVED):
        service.advance(intent, expected_ledger_head=head)


@pytest.mark.parametrize("value", [(-1, "0" * 64), (1, "A" * 64), (1, "0" * 63), ("1", "0" * 64), [1, "0" * 64]])
def test_a_malformed_checked_head_is_refused(tmp_path: Path, value) -> None:
    service = StoreBindingService.__new__(StoreBindingService)
    with pytest.raises(ConfigurationError, match="expected ledger head must be"):
        StoreBindingService.advance(service, None, expected_ledger_head=value)  # type: ignore[arg-type]


# --- The command path: ars store advance-binding --expected-ledger-head -------------------------------------------------


def _intent_file(tmp_path: Path, intent) -> Path:
    path = tmp_path / "advance-intent.json"
    mapping = {
        "schema_id": ADVANCE_INTENT_SCHEMA_ID,
        "schema_version": "1.2.0",
        "command_type": "AdvanceStoreBinding",
        **intent.semantic_payload(),
    }
    path.write_bytes(canonical_bytes(mapping))
    return path


def _cli_service(monkeypatch: pytest.MonkeyPatch, service: StoreBindingService) -> None:
    monkeypatch.setattr(
        cli,
        "StoreBindingService",
        functools.partial(StoreBindingService, now=lambda: _NOW, foundation_path=service.foundation_path),
    )


def test_the_command_refuses_on_a_moved_head_and_advances_on_a_matching_one(tmp_path, monkeypatch, capsys) -> None:
    service, intent, _ = _prepared(tmp_path)
    _cli_service(monkeypatch, service)
    path = _intent_file(tmp_path, intent)
    position, event_hash = _head(service)
    stale = f"{position - 1}:{service.ledger.snapshot().events[-2]['event_hash']}"
    with pytest.raises(ConflictError, match=MOVED):
        cli.main(["store", "advance-binding", "--intent", str(path), "--expected-ledger-head", stale])
    assert (
        cli.main(
            ["store", "advance-binding", "--intent", str(path), "--expected-ledger-head", f"{position}:{event_hash}"]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "advanced"


@pytest.mark.parametrize("value", ["12", "x:" + "0" * 64, "1:" + "0" * 63, "01:" + "0" * 64, "1:" + "G" * 64])
def test_the_command_refuses_a_malformed_head_before_the_service_runs(tmp_path, monkeypatch, value: str) -> None:
    def never(*args, **kwargs):
        raise AssertionError("the service must not run")

    monkeypatch.setattr(cli, "StoreBindingService", never)
    monkeypatch.setattr(cli, "read_advance_intent", never)
    with pytest.raises(ConfigurationError, match="--expected-ledger-head must be"):
        cli.main(["store", "advance-binding", "--intent", str(tmp_path / "x.json"), "--expected-ledger-head", value])
