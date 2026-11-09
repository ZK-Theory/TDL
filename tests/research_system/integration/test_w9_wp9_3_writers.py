# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §4.3, §9.1, §13)
# Purpose: W9 identities at the W11, generic and T2 writers; the in-lock binding recheck; the pre-pin check; the CLI.
"""WP9.3-1 writer controls (WP9.3 note §4.3, §9.1, §13, §17). Every store is a scratch store under ``tmp_path``."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import research_system.legacy.identities as identities
from research_system import cli
from research_system.errors import ConflictError, IntegrityError
from research_system.ids import new_id
from research_system.legacy.accepted_w9 import ACCEPTED, CATALOGUE_STREAM_ID, RESERVED_IDS
from research_system.legacy.records import w0_signature_ref_id
from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes, _write_manifest
from tests.research_system.integration.test_wp6_1_task_scope_lifecycle import _command, _scope_create_payload
from tests.research_system.integration.test_wp6_6_discovery_runtime import _HARNESSES, _ingest_candidate, _runtime
from tests.research_system.integration.w9_runtime_harness import W9Store, w9_store

FIXED = "command would take a W9 fixed identity"
CLAIMED = "command would take an identity W9 claims or reserves"
REVALIDATE_FAILED = "current store binding changed during the operation"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> W9Store:
    return w9_store(tmp_path, monkeypatch)


def _proposed(store: W9Store) -> dict[str, Any]:
    payload = store.registration_payload("results/x.json")
    assert store.submit("ProposeLegacyRecord", store.actors.analyst, payload["record_id"], 0, payload).status == (
        "accepted"
    )
    return payload


def _scope(target: str) -> dict[str, Any]:
    return _command(
        new_id("command"), "CreateScopeDefinition", target, 0, _scope_create_payload(target, completion="c")
    )


# --- The W11 writer (§4.3) ---------------------------------------------------------------------------------------------


def test_a_w11_minting_command_on_w9s_catalogue_stream_is_refused_before_w9_genesis(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    from tests.research_system.integration.test_wp6_6_discovery_runtime import _genesis

    runtime.submit(_genesis())
    before = tuple(_HARNESSES[tmp_path].ledger.iter_events())
    with pytest.raises(IntegrityError, match=FIXED):
        _ingest_candidate(runtime, new_id("scope_definition"), observation_id=CATALOGUE_STREAM_ID, title="t")
    assert tuple(_HARNESSES[tmp_path].ledger.iter_events()) == before


def test_w11_commands_on_w9_identities_are_refused_after_w9_genesis(store: W9Store, tmp_path: Path) -> None:
    payload = _proposed(store)
    runtime = _runtime(tmp_path)
    before = store.events()
    # After W9 genesis the catalogue stream is at version 1, so the command names that version to pass the
    # stream-version check and reach the identity check.
    with pytest.raises(IntegrityError, match=FIXED):
        _ingest_candidate(
            runtime,
            new_id("scope_definition"),
            observation_id=CATALOGUE_STREAM_ID,
            title="t",
            expected_stream_version=1,
        )
    # A W9-claimed record ID as the candidate a W11 batch would create (a created ID, not the target stream).
    with pytest.raises(IntegrityError, match=CLAIMED):
        _ingest_candidate(runtime, payload["record_id"], observation_id=new_id("scope_definition"), title="t")
    assert store.events() == before


# --- The generic and T2 writers (§4.3) --------------------------------------------------------------------------------


def test_a_generic_scope_on_w9s_catalogue_stream_is_refused_before_w9_genesis(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    del runtime
    harness = _HARNESSES[tmp_path]
    before = tuple(harness.ledger.iter_events())
    with pytest.raises(IntegrityError, match=FIXED):
        harness.service.submit(_scope(CATALOGUE_STREAM_ID))
    assert tuple(harness.ledger.iter_events()) == before


def test_generic_creations_on_w9_identities_are_refused_after_w9_genesis(store: W9Store) -> None:
    payload = _proposed(store)
    before = store.events()
    # Both streams exist at version 1, so each command names that version to reach the identity check.
    for target, message in ((CATALOGUE_STREAM_ID, FIXED), (payload["record_id"], CLAIMED)):
        command = _scope(target)
        command["expected_stream_version"] = 1
        with pytest.raises(IntegrityError, match=message):
            store.harness.service.submit(command)
    assert store.events() == before
    # A generic creation on an ID W9 does not hold is admitted, so the refusal is the W9 check's.
    assert store.harness.service.submit(_scope(new_id("scope_definition"))).status == "accepted"


def test_a_t2_creation_on_a_w9_reserved_id_is_refused_before_append(tmp_path: Path, monkeypatch) -> None:
    import research_system.command.t2 as t2
    from tests.research_system.unit.test_wp6_2_t2_runtime import _service, issue_command

    service, ledger, _, _ = _service(tmp_path)
    original = t2._events_for

    def onto_a_reserved_id(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        events = original(*args, **kwargs)
        events[0] = {**events[0], "stream_id": sorted(RESERVED_IDS)[0]}
        return events

    monkeypatch.setattr(t2, "_events_for", onto_a_reserved_id)
    with pytest.raises(IntegrityError, match=FIXED):
        service.submit(issue_command())
    assert tuple(ledger.iter_events()) == ()


# --- The in-lock binding recheck (§9.1) --------------------------------------------------------------------------------


def _revalidate_after_an_advance() -> None:
    raise ConflictError(REVALIDATE_FAILED)


def test_a_w9_submit_paused_across_an_advance_is_refused_inside_its_lock(store: W9Store) -> None:
    payload = store.registration_payload("results/x.json")
    store.runtime.binding_check = _revalidate_after_an_advance
    before = store.events()
    with pytest.raises(ConflictError, match=REVALIDATE_FAILED):
        store.submit("ProposeLegacyRecord", store.actors.analyst, payload["record_id"], 0, payload)
    assert store.events() == before


def test_a_w11_submit_paused_across_an_advance_is_refused_inside_its_lock(tmp_path: Path) -> None:
    from tests.research_system.integration.test_wp6_6_discovery_runtime import _genesis

    runtime = _runtime(tmp_path)
    runtime.binding_check = _revalidate_after_an_advance
    with pytest.raises(ConflictError, match=REVALIDATE_FAILED):
        runtime.submit(_genesis())
    assert tuple(_HARNESSES[tmp_path].ledger.iter_events()) == tuple(
        event
        for event in _HARNESSES[tmp_path].ledger.iter_events()
        if event["command_type"] != "ImportAcceptedW11CatalogueGenesis"
    )


def test_generic_submits_and_the_locked_authority_path_recheck_the_binding(store: W9Store) -> None:
    service = store.harness.service
    service.binding_check = _revalidate_after_an_advance
    before = store.events()
    with pytest.raises(ConflictError, match=REVALIDATE_FAILED):
        service.submit(_scope(new_id("scope_definition")))
    with pytest.raises(ConflictError, match=REVALIDATE_FAILED):
        service.with_locked_authority(
            authority_grant_id=new_id("authority_grant"),
            actor_id=store.actors.analyst,
            command_type="CreateScopeDefinition",
            project_id=store.harness.ledger.project_id,
            subject_kind="scope_definition",
            subject_id=new_id("scope_definition"),
            callback=lambda resolved: pytest.fail("the callback must not run"),
        )
    assert store.events() == before


def test_a_t2_submit_rechecks_the_binding_inside_submission_lock(tmp_path: Path) -> None:
    from tests.research_system.unit.test_wp6_2_t2_runtime import _service, issue_command

    service, ledger, _, _ = _service(tmp_path)
    service.binding_check = _revalidate_after_an_advance
    with pytest.raises(ConflictError, match=REVALIDATE_FAILED):
        service.submit(issue_command())
    assert tuple(ledger.iter_events()) == ()


# --- The pre-pin check (§9.1) ------------------------------------------------------------------------------------------

DOMAIN = "w9-external:decision:P-999:docs/plans/agentic-research-system/03-decisions-and-open-questions.md@" + "a" * 40
ACCEPTED_AT = "2026-12-01T00:00:00Z"


@pytest.mark.parametrize("writer", ["w11", "generic"])
def test_the_pre_pin_check_finds_a_non_w9_stream_on_the_candidate_and_re_derives_it(
    store: W9Store, tmp_path: Path, monkeypatch, writer: str
) -> None:
    """A W11 stream, and separately a generic stream, on the candidate's derived ID (§9.1, §17).

    The signature ref is a ``dec_``, which no W11 or generic writer in these harnesses mints, so the test derives the
    candidate as an ``obj_`` from the same domain rule; the collision and re-derivation mechanics do not depend on the
    prefix.
    """
    import research_system.legacy.records as records

    def obj_candidate(domain: str, accepted_at: str, suffix: int | None = None) -> str:
        return records.derived_id(
            "obj", domain if suffix is None else f"{domain}#{suffix}", records.utc_milliseconds(accepted_at)
        )

    monkeypatch.setattr(records, "w0_signature_ref_id", obj_candidate)
    candidate = obj_candidate(DOMAIN, ACCEPTED_AT)
    if writer == "w11":
        _ingest_candidate(_runtime(tmp_path), new_id("scope_definition"), observation_id=candidate, title="t")
    else:
        assert store.harness.service.submit(_scope(candidate)).status == "accepted"
    ledger = store.harness.ledger
    check = identities.check_w0_pin_candidate(ledger, candidate, schemas=store.harness.schemas)
    assert not check.passed
    assert any("takes the candidate" in collision for collision in check.collisions)
    selected = identities.select_w0_signature_ref(ledger, DOMAIN, ACCEPTED_AT, schemas=store.harness.schemas)
    assert selected.passed and selected.candidate_id == obj_candidate(DOMAIN, ACCEPTED_AT, 1)


def test_the_pre_pin_check_records_the_head_of_the_one_snapshot_it_scanned(store: W9Store, monkeypatch) -> None:
    candidate = w0_signature_ref_id(DOMAIN, ACCEPTED_AT)
    ledger = store.harness.ledger
    before = ledger.snapshot()
    appended: list[int] = []
    original = identities.created_ids

    def append_during_the_scan(event: dict[str, Any]) -> frozenset[str]:
        if not appended:
            appended.append(1)
            payload = store.registration_payload("tracker.md")
            store.submit("ProposeLegacyRecord", store.actors.analyst, payload["record_id"], 0, payload)
        return original(event)

    monkeypatch.setattr(identities, "created_ids", append_during_the_scan)
    check = identities.check_w0_pin_candidate(ledger, candidate, schemas=store.harness.schemas)
    after = ledger.snapshot()
    assert appended and after.global_position == before.global_position + 1
    assert (check.global_position, check.event_hash) == (before.global_position, before.event_hash)
    assert check.expected_ledger_head == f"{before.global_position}:{before.event_hash}"


# --- The CLI (§13) -----------------------------------------------------------------------------------------------------


def _envelope_file(tmp_path: Path, envelope: dict[str, Any]) -> Path:
    path = tmp_path / f"{envelope['command_id']}.json"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    return path


def _pin_foundation_path(monkeypatch, root: Path) -> None:
    """Point the CLI's canonical foundation at a scratch path, so no test reads the committed one."""
    path = root / "repository" / ".research-system" / "config" / "foundation.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: path)


def _bind_cli_to(store: W9Store, monkeypatch) -> None:
    """Stub the current binding as tests that read the foundation must (§13); the loader is tested on its own."""
    _pin_foundation_path(monkeypatch, store.repo.parent)
    binding = SimpleNamespace(
        control_root=store.harness.ledger.control_root,
        project_id=store.harness.ledger.project_id,
        store_identity="a" * 64,
        repository_root=store.repo,
        schema_root=Path(__file__).resolve().parents[3] / ".research-system" / "schemas",
        origin_witness=None,
        origin_witness_path=None,
        binding={"git_head": store.head},
        revalidate=lambda: None,
    )
    import research_system.store.current_binding as current_binding

    monkeypatch.setattr(current_binding, "load_current_binding", lambda **kwargs: binding)
    monkeypatch.setattr(cli, "LedgerAuthorityGrantResolver", lambda *args, **kwargs: store.runtime.authority_resolver)
    import research_system.legacy.runtime as legacy_runtime

    original = legacy_runtime.LegacyRuntime

    def bound_runtime(*args: Any, **kwargs: Any) -> Any:
        kwargs["repository_root"] = Path(__file__).resolve().parents[3]
        kwargs["clock"] = store.clock
        return original(*args, **kwargs)

    monkeypatch.setattr(legacy_runtime, "LegacyRuntime", bound_runtime)


def _never_bind(monkeypatch) -> None:
    import research_system.store.current_binding as current_binding

    def bound(**kwargs: Any) -> Any:
        raise AssertionError("bound a refused store")

    monkeypatch.setattr(current_binding, "load_current_binding", bound)
    monkeypatch.setattr(cli, "_verified_ledger", bound)


def test_ars_legacy_submit_refuses_a_gate6_root_and_a_root_nested_in_one_before_binding(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _never_bind(monkeypatch)
    _pin_foundation_path(monkeypatch, tmp_path)
    gate6 = tmp_path / "gate6"
    _write_manifest(gate6, ACCEPTED["gate6_store_identity"])
    nested = gate6 / "nested" / "control"
    _write_manifest(nested, "b" * 64)
    envelope = _envelope_file(tmp_path, {"command_id": new_id("command"), "command_type": "ProposeLegacyRecord"})
    for root in (gate6, nested):
        before = _tree_bytes(gate6)
        assert cli.main(["legacy", "submit", str(envelope), "--control-root", str(root)]) == 1
        assert "w9_gate6_store_refused" in capsys.readouterr().err
        assert _tree_bytes(gate6) == before


def test_ars_legacy_submit_accepts_a_command_on_a_valid_scratch_store(store: W9Store, monkeypatch, capsys) -> None:
    _bind_cli_to(store, monkeypatch)
    payload = store.registration_payload("results/x.json")
    envelope = store.envelope("ProposeLegacyRecord", store.actors.analyst, payload["record_id"], 0, payload)
    path = _envelope_file(store.repo.parent, envelope)
    assert cli.main(["legacy", "submit", str(path), "--control-root", str(store.harness.ledger.control_root)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"


def test_ars_legacy_observation_id_prints_the_preparers_id_and_writes_nothing(store: W9Store, monkeypatch, capsys):
    _bind_cli_to(store, monkeypatch)
    registration = store.register("results/x.json")
    payload = store.observation_payload(registration)
    printed_envelope = store.envelope(
        "ObserveLegacyRecord", store.actors.observer, new_id("scope_definition"), 0, payload
    )
    path = _envelope_file(store.repo.parent, printed_envelope)
    monkeypatch.setattr(cli, "_legacy_projection", lambda root: (_state(store), 0))
    control = store.harness.ledger.control_root
    before = _tree_bytes(control)
    assert cli.main(["legacy", "observation-id", str(path), "--control-root", str(control)]) == 0
    printed = json.loads(capsys.readouterr().out)["record_id"]
    assert _tree_bytes(control) == before
    store.clock.advance(hours=3)
    receipt = store.submit("ObserveLegacyRecord", store.actors.observer, printed, 0, payload)
    assert receipt.status == "accepted"


def _state(store: W9Store) -> dict[str, Any]:
    from research_system.legacy.replay.driver import replay_legacy

    return replay_legacy(store.events(), schemas=store.harness.schemas)


def test_ars_legacy_observation_id_refuses_a_gate6_root_before_binding(tmp_path: Path, monkeypatch, capsys) -> None:
    _never_bind(monkeypatch)
    _pin_foundation_path(monkeypatch, tmp_path)
    gate6 = tmp_path / "gate6"
    _write_manifest(gate6, ACCEPTED["gate6_store_identity"])
    envelope = {"command_id": new_id("command"), "command_type": "ObserveLegacyRecord", "payload": {}}
    path = _envelope_file(tmp_path, envelope)
    before = _tree_bytes(gate6)
    assert cli.main(["legacy", "observation-id", str(path), "--control-root", str(gate6)]) == 1
    assert "w9_gate6_store_refused" in capsys.readouterr().err
    assert _tree_bytes(gate6) == before
