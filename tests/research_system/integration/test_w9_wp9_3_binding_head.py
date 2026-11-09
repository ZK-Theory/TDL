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


# --- Pin release by a binding advance, through load_current_binding itself (§9.1, §17) ----------------------------------

PIN_LINE = "# A later W0 pin lands here (a test stand-in for an ACCEPTED_W0_SIGNATURES entry).\n"


def _pin_intent(tmp_path: Path):
    """The v1.2 advance fixture, whose reviewed change is a later pin: it changes ``accepted_w9.py``, governed code."""
    import shutil

    from research_system.store.binding_service import AdvanceStoreBinding
    from research_system.store.current_binding import load_current_binding
    from research_system.store.governed_code import build_governed_code_manifest
    from tests.research_system.factories import PROJECT_ID
    from tests.research_system.integration.test_store_binding_service import (
        _admitted_legacy_predecessor,
        _git,
        _git_text,
    )

    service, repair, predecessor_root, predecessor_sha256 = _admitted_legacy_predecessor(tmp_path)
    pinned = tmp_path / "pinned"
    shutil.copytree(predecessor_root, pinned)
    _git(pinned, "config", "user.email", "gate6@example.invalid")
    _git(pinned, "config", "user.name", "Gate 6")
    accepted = pinned / "research_system" / "legacy" / "accepted_w9.py"
    accepted.write_bytes(accepted.read_bytes() + PIN_LINE.encode())
    _git(pinned, "add", ".")
    _git(pinned, "commit", "-m", "a later W0 pin")
    pinned = pinned.resolve()
    head = _git_text(pinned, "rev-parse", "HEAD")
    predecessor = load_current_binding(
        foundation_path=predecessor_root / ".research-system" / "config" / "foundation.yaml",
        repository_root=predecessor_root,
        expected_control_root=service.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=service.store_identity,
        expected_binding_sha256=predecessor_sha256,
    )
    intent = AdvanceStoreBinding(
        service.control_root,
        pinned,
        PROJECT_ID,
        service.store_identity,
        repair.expected_origin_authority_root,
        repair.expected_origin_witness_sha256,
        pinned / ".research-system" / "schemas",
        "2026-08-24T11:00:00Z",
        "2026-08-24T13:00:00Z",
        repair.owner_actor_id,
        "advance-reviewed-divergence-store-binding",
        "w9-pin-release",
        "release a later W0 pin by a binding advance (WP9.3 note §9.1)",
        predecessor_sha256,
        head,
        head,
        "refs/heads/main",
        {
            "predecessor_binding_sha256": predecessor_sha256,
            "predecessor_git_head": predecessor.binding["git_head"],
            "candidate_git_head": head,
            "integration_ref": "refs/heads/main",
            "protected_route_sha256": predecessor.binding["route"]["sha256"],
            "protected_sources_sha256": sha256_hex(canonical_bytes(predecessor.binding["sources"])),
            "governed_code_manifest_sha256": build_governed_code_manifest(pinned).manifest_sha256,
        },
    )
    return service, intent, predecessor_root, pinned, predecessor


def _admit(service: StoreBindingService, root: Path):
    from research_system.store.current_binding import load_current_binding
    from tests.research_system.factories import PROJECT_ID

    return load_current_binding(
        foundation_path=root / ".research-system" / "config" / "foundation.yaml",
        repository_root=root,
        expected_control_root=service.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=service.store_identity,
    )


def test_a_later_pin_is_released_by_a_binding_advance_and_pre_pin_code_is_refused(tmp_path, monkeypatch, capsys):
    from research_system.errors import ArsError
    from tests.research_system.integration.test_store_binding_service import _git

    service, intent, predecessor_root, pinned, predecessor = _pin_intent(tmp_path)
    # Before the advance, the pinned checkout changes governed code, so the binding refuses it.
    with pytest.raises(ArsError):
        _admit(service, pinned)
    result = service.advance(intent)
    assert result["status"] == "advanced"
    # After it: the pinned checkout is admitted; the old checkout is refused by the code-root check, and a process
    # that admitted before the advance is refused on its next admission (its revalidate).
    assert _admit(service, pinned).binding_sha256 == result["binding_sha256"]
    with pytest.raises(ArsError):
        _admit(service, predecessor_root)
    with pytest.raises(ArsError):
        predecessor.revalidate()
    # The binding names one code root, so the ancestry checks run in the bound checkout itself. A checkout at the
    # pin's parent is refused: with refs/heads/main left at the bound commit, and with it rewound to the parent.
    from tests.research_system.integration.test_store_binding_service import _git_text

    bound = _git_text(pinned, "rev-parse", "HEAD")
    _git(pinned, "checkout", "--detach", "HEAD~1")
    with pytest.raises(ArsError):
        _admit(service, pinned)
    _git(pinned, "checkout", "main")
    _git(pinned, "reset", "--hard", "HEAD~1")
    with pytest.raises(ArsError):
        _admit(service, pinned)
    _git(pinned, "reset", "--hard", bound)
    assert _admit(service, pinned).binding_sha256 == result["binding_sha256"]
    # A documentation-only descendant of the pin on main is admitted.
    (pinned / "docs").mkdir(exist_ok=True)
    (pinned / "docs" / "pin-note.md").write_text("documentation only\n", encoding="utf-8")
    _git(pinned, "add", ".")
    _git(pinned, "commit", "-m", "documentation only")
    assert _admit(service, pinned).binding_sha256 == result["binding_sha256"]
    # ars legacy submit from the pre-pin checkout is refused before it replays or appends.
    events_before = tuple(service.ledger.iter_events())
    monkeypatch.setattr(
        cli, "canonical_foundation_path", lambda: predecessor_root / ".research-system" / "config" / "foundation.yaml"
    )
    envelope = tmp_path / "envelope.json"
    envelope.write_text(json.dumps({"command_type": "ProposeLegacyRecord"}), encoding="utf-8")
    assert cli.main(["legacy", "submit", str(envelope), "--control-root", str(service.control_root)]) == 1
    assert "error:" in capsys.readouterr().err
    assert tuple(service.ledger.iter_events()) == events_before


def test_a_pin_committed_in_place_in_the_bound_checkout_cannot_be_advanced(tmp_path: Path) -> None:
    """The pin goes in a separate checkout; updated in place, the predecessor's re-admission refuses the advance."""
    from dataclasses import replace

    from research_system.errors import ArsError
    from tests.research_system.integration.test_store_binding_service import _git

    service, intent, predecessor_root, _, _ = _pin_intent(tmp_path)
    accepted = predecessor_root / "research_system" / "legacy" / "accepted_w9.py"
    accepted.write_bytes(accepted.read_bytes() + PIN_LINE.encode())
    _git(predecessor_root, "add", ".")
    _git(predecessor_root, "commit", "-m", "the pin, in place")
    pointer = (service.control_root / "manifests" / "binding-repair-current.json").read_bytes()
    with pytest.raises(ArsError):
        service.advance(replace(intent, candidate_repository_root=predecessor_root))
    assert (service.control_root / "manifests" / "binding-repair-current.json").read_bytes() == pointer
