# Research context: docs/plans/agentic-research-system/transition/w9/wp9-2-design-note.md (WP9.2-2; P-076, P-077)
# Purpose: W9 shared-ledger replay on forged scratch ledgers: the four U-7 sites, C1-C3, payloads and route classes.
"""W9 legacy replay controls on forged ledgers (06v WP9.2; design note §§2, 3, 4, 7.3, 9).

The base ledger is a scratch store holding W11 genesis and a real W9 genesis (through ``LegacyRuntime``). Forged W9
events are appended to a copy and re-hashed; nothing is written back. A test registry adds the binding rows WP9.2 does
not admit, as the U-7 probe did, and a test route set routes the rows whose reducers are exercised.
"""

from __future__ import annotations

import functools
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import research_system.legacy.accepted_w9 as accepted_w9
import research_system.legacy.commands as legacy_commands
import research_system.legacy.replay.driver as legacy_driver
import research_system.legacy.routes as legacy_routes
import research_system.schema_registry as registry_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy.accepted_w9 import RESERVED_EXTERNAL_REFS
from research_system.legacy.replay import reducers
from research_system.legacy.replay.driver import replay_legacy
from research_system.legacy.routes import LEGACY_ROW_ROUTES, W2_EVENT_TYPES, verdict_row_for_request
from research_system.projection.replay import _validate_active_lifecycle_binding, rebuild_projection
from research_system.projection.replay import replay as replay_projection
from research_system.schema_registry import SchemaBinding
from tests.research_system.contracts.test_w9_contract_materialization import (
    _acceptance,
    _header,
    _load_tool,
    _observation,
    _paper_root,
    _tracked,
    _transition,
)
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_legacy_runtime import _genesis_command, _store
from tests.research_system.integration.test_wp6_6_discovery_runtime import _rehash_events

SCHEMA_ROOT = Path(registry_module.__file__).resolve().parent.parent / ".research-system" / "schemas"
# The W9 commands no runtime binding row admits after WP9.3-1 (WP9.3 note §2.2): the test registry adds them.
W9_BINDINGS = tuple(
    SchemaBinding("ars://core/command", "1.0.0", command_type=name)
    for name in sorted(
        legacy_commands.LEGACY_COMMAND_TYPES
        - {binding.command_type for binding in registry_module._RUNTIME_BINDINGS if binding.command_type}
    )
)
# Production since WP9.3-1 (note §16); the C2 controls remove it inside the test (note §17, review m-4).
REVIEW_PRODUCER = SchemaBinding(
    "ars://core/event/ReviewRequested",
    "1.0.0",
    event_type="ReviewRequested",
    producer_command_type="RequestW9AuthorityReview",
)
TEST_ROUTES = legacy_routes.LEGACY_ROUTED_ROWS
# Every row, for the reducer tests (review F-3).
ALL_ROWS = frozenset(LEGACY_ROW_ROUTES)
# C1: the Discovery envelope validator's refusal of a W9 command with no active binding row (review F-6).
C1_MESSAGE = "Discovery persisted schema provenance mismatch"


def _registry(
    monkeypatch: pytest.MonkeyPatch,
    extra: tuple[SchemaBinding, ...] = (),
    without: tuple[SchemaBinding, ...] = (),
) -> Any:
    bindings = tuple(binding for binding in registry_module._RUNTIME_BINDINGS if binding not in without)
    assert len(bindings) == len(registry_module._RUNTIME_BINDINGS) - len(without), "a removed row was not bound"
    monkeypatch.setattr(registry_module, "_RUNTIME_BINDINGS", (*bindings, *extra))
    cached = registry_module._runtime_registry_for_resolved_root
    if hasattr(cached, "cache_clear"):
        cached.cache_clear()
    return registry_module.runtime_schema_registry(SCHEMA_ROOT)


@pytest.fixture(autouse=True)
def _fresh_registry_cache() -> Any:
    """A test registry must not outlive its test through the registry cache."""
    yield
    cached = registry_module._runtime_registry_for_resolved_root
    if hasattr(cached, "cache_clear"):
        cached.cache_clear()


def _route(monkeypatch: pytest.MonkeyPatch, rows: frozenset[str] = TEST_ROUTES) -> None:
    """Route test rows at the generic boundary too: site 4 imports replay_legacy from the driver at call time."""
    monkeypatch.setattr(legacy_driver, "replay_legacy", functools.partial(replay_legacy, routed_rows=rows))


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> tuple[tuple[dict[str, Any], ...], Any]:
    tmp_path = tmp_path_factory.mktemp("w9-replay")
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    return tuple(harness.ledger.iter_events()), harness.schemas


def _forge_transaction(
    events: tuple[dict[str, Any], ...], command_type: str, members: list[tuple[str, dict[str, Any], str]]
) -> tuple[dict[str, Any], ...]:
    """Append one W9 transaction of ``(event_type, payload, schema_id)`` members and re-hash the copy."""
    template = next(event for event in events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis")
    command_id = new_id("command")
    transaction_id = new_id("event_batch")
    forged = []
    for index, (event_type, payload, schema_id) in enumerate(members, start=1):
        event = deepcopy(template)
        event.update(
            {
                "event_id": new_id("event"),
                "global_position": len(events) + index,
                "stream_id": new_id("scope_definition"),
                "stream_version": 1,
                "transaction_id": transaction_id,
                "transaction_index": index,
                "transaction_count": len(members),
                "command_id": command_id,
                "command_type": command_type,
                "event_type": event_type,
                "schema_id": schema_id,
                "schema_version": "1.0.0",
                "idempotency_key": f"w9-test:{command_id}",
                "command_payload_hash": sha256_hex(canonical_bytes(members[0][1])),
                "correlation_id": command_id,
                "payload": payload,
            }
        )
        forged.append(event)
    return _rehash_events((*events, *forged))


def _forge(
    events: tuple[dict[str, Any], ...],
    command_type: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    schema_id: str = "ars://core/event",
) -> tuple[dict[str, Any], ...]:
    return _forge_transaction(events, command_type, [(event_type, payload, schema_id)])


def _observed(events: tuple[dict[str, Any], ...], record: dict[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    return _forge(events, "ObserveLegacyRecord", "LegacyRecordObserved", record or _observation(_tracked()))


def _review_request(row: str = "LR-007", **overrides: Any) -> dict[str, Any]:
    payload = {
        "review_type": "migration",
        "new_review_id": new_id("review"),
        "subject_ids": [new_id("scope_definition")],
        "subject_hashes": ["a" * 64],
        "governing_refs": [f"W9:{row}"],
        "review_questions": ["Is the membership table independently reproduced?"],
        "required_evidence_refs": ["w9:membership"],
        "required_lanes": ["provenance"],
        "reviewer_capability": ["w9-independent-review"],
        "required_independence_grade": "independent",
        "visibility_policy": "owner-visible",
        "allowed_verdicts": ["approve", "changes_requested", "reject"],
        "satisfaction_authority": "ars://legacy/policy/w9-review@1.0.0",
        "deadline": "2026-11-12T00:00:00Z",
        "escalation_rule": "owner-ruling",
    }
    payload.update(overrides)
    return payload


# --- The shared-replay test and its negative controls (design note §9) ------------------------------------------


def test_shared_replay_with_an_observation_and_a_w2_typed_w9_event(base, monkeypatch, tmp_path) -> None:
    """WP9.3-1 routes LR-015 and LR-007, so the flow is a valid one (WP9.3 note §6) on the production registry."""
    events, schemas = base
    pin = flows.signature()
    monkeypatch.setattr(accepted_w9, "ACCEPTED_W0_SIGNATURES", (pin,))
    actors = flows.Actors(owner=_owner(events))
    forger, registration = flows.registered(flows.Forger(events), actors)
    forger, _ = flows.membership_recorded(forger, actors, sha256="a" * 64, size=1, stop_after="LR-007")
    observation = flows.observation(forger.project_id, actors.observer, flows.at(30), registration, pin)
    forger = forger.row("LR-015", observation["record_id"], observation, actor=actors.observer, when=flows.at(30))
    ledger = forger.events
    replay_projection(ledger, schema_registry=schemas)
    rebuild_projection(ledger, tmp_path / "projection.json", schemas)
    replay_discovery(ledger, schemas=schemas)
    state = replay_legacy(ledger, schemas=schemas)
    assert state["row_counts"] == {
        "LR-001": 1,
        "LR-003": 1,
        "LR-004": 1,
        "LR-005": 1,
        "LR-006": 1,
        "LR-007": 1,
        "LR-015": 1,
    }


def test_negative_control_predicate_removed(base, monkeypatch) -> None:
    events, schemas = base
    monkeypatch.setattr(legacy_commands, "is_legacy_projection_event", lambda event: False)
    with pytest.raises(IntegrityError, match="unsupported event type: W9CatalogueGenesisImported"):
        replay_projection(events, schema_registry=schemas)
    with pytest.raises(IntegrityError, match="invalid Discovery operational partition"):
        replay_discovery(events, schemas=schemas)


def test_negative_control_site_3_removed(base, monkeypatch) -> None:
    """Without site 3's branch a legacy event falls through to the Discovery reducer table."""
    events, schemas = base
    import research_system.discovery.replay.driver as discovery_driver

    partition = discovery_driver._shared_event_partition

    def without_site_3(event: dict[str, Any], **kwargs: Any) -> str:
        value = partition(event, **kwargs)
        return "unhandled" if value == "legacy" else value

    monkeypatch.setattr(discovery_driver, "_shared_event_partition", without_site_3)
    with pytest.raises(IntegrityError, match="unsupported Discovery event: W9CatalogueGenesisImported"):
        replay_discovery(events, schemas=schemas)


def test_negative_control_lifecycle_check_restored_at_site_1(base, monkeypatch) -> None:
    events, _ = base
    schemas = _registry(monkeypatch, W9_BINDINGS)
    ledger = _forge(
        events,
        "RequestW9AuthorityReview",
        "ReviewRequested",
        _review_request(),
        schema_id="ars://core/event/ReviewRequested",
    )
    with pytest.raises(IntegrityError, match="exact lifecycle event provenance mismatch"):
        _validate_active_lifecycle_binding(ledger[-1], schemas)


# --- C1, C2, C3 ------------------------------------------------------------------------------------------------------


def test_c1_a_w9_command_without_its_binding_row_is_refused(base, monkeypatch) -> None:
    """WP9.3-1 binds ObserveLegacyRecord, so the control removes the row inside the test (WP9.3 note §17, m-4)."""
    events, _ = base
    schemas = _registry(
        monkeypatch, without=(SchemaBinding("ars://core/command", "1.0.0", command_type="ObserveLegacyRecord"),)
    )
    _route(monkeypatch)
    with pytest.raises(IntegrityError, match=C1_MESSAGE):
        replay_projection(_observed(events), schema_registry=schemas)


@pytest.mark.parametrize(
    ("schema_id", "message"),
    [
        # Recorded under its W2 schema: the shared replay finds no active binding for that schema.
        ("ars://core/event/ReviewRequested", "inactive event schema: ars://core/event/ReviewRequested"),
        # Recorded as ars://core/event, as the U-7 probe did: the Discovery envelope validator finds no producer.
        ("ars://core/event", "unbound event producer"),
    ],
)
def test_c2_a_w2_typed_event_without_its_producer_binding_is_refused(base, monkeypatch, schema_id, message) -> None:
    """WP9.3-1 binds the producer row, so the control removes it inside the test (WP9.3 note §17, m-4)."""
    events, _ = base
    schemas = _registry(monkeypatch, W9_BINDINGS, without=(REVIEW_PRODUCER,))
    _route(monkeypatch)
    ledger = _forge(events, "RequestW9AuthorityReview", "ReviewRequested", _review_request(), schema_id=schema_id)
    with pytest.raises(IntegrityError) as refused:
        replay_discovery(ledger, schemas=schemas)
    assert message in f"{refused.value} {refused.value.__cause__}"


def test_c2_a_w2_typed_event_recorded_as_core_event_is_refused(base, monkeypatch) -> None:
    events, _ = base
    schemas = _registry(monkeypatch, W9_BINDINGS)
    _route(monkeypatch)
    ledger = _forge(events, "RequestW9AuthorityReview", "ReviewRequested", _review_request())
    with pytest.raises(IntegrityError) as refused:
        replay_discovery(ledger, schemas=schemas)
    assert "active event binding mismatch" in f"{refused.value} {refused.value.__cause__}"
    with pytest.raises(IntegrityError, match="recorded under another schema"):
        replay_legacy(ledger, schemas=schemas, routed_rows=TEST_ROUTES)


def test_c3_a_w9_payload_naming_a_w11_row_is_refused(base) -> None:
    events, schemas = base
    ledger = _forge(
        events,
        "RequestW9AuthorityReview",
        "ReviewRequested",
        _review_request(governing_refs=["W9:LR-007", "W11:OR-010"]),
        schema_id="ars://core/event/ReviewRequested",
    )
    with pytest.raises(IntegrityError, match="names a W11 owner row"):
        replay_legacy(ledger, schemas=schemas, routed_rows=TEST_ROUTES)


# --- Payloads, route classes and genesis at replay -------------------------------------------------------------------


def test_a_deferred_row_is_refused(base) -> None:
    """LR-016 stays deferred to WP9.3-2, and LR-023 to WP9.4, though ProposeLegacyRecord is bound (note §2.2)."""
    events, schemas = base
    for kind, row, tag in (
        ("legacy-closed-reference-acceptance", "LR-016", "WP9.3"),
        ("legacy-adoption-decision", "LR-023", "WP9.4"),
    ):
        event_type = LEGACY_ROW_ROUTES[row].events[0].event_type
        ledger = _forge(events, "ProposeLegacyRecord", event_type, {"schema_id": f"ars://legacy/{kind}"})
        with pytest.raises(IntegrityError, match=rf"W9 row not routed in this version: {row} \({tag}\)"):
            replay_legacy(ledger, schemas=schemas)


def test_a_schema_invalid_payload_is_refused(base) -> None:
    events, schemas = base
    record = _observation(_tracked())
    del record["observer_actor_id"]
    with pytest.raises(IntegrityError, match="does not validate against its record schema"):
        replay_legacy(_observed(events, record), schemas=schemas, routed_rows=TEST_ROUTES)


def test_a_restricted_source_without_a_frozen_copy_replays(base) -> None:
    """The schema refuses a restricted source with a frozen copy before the reducer; the reducer half is unit-tested."""
    events, schemas = base
    pin = flows.signature()
    actors = flows.Actors(owner=_owner(events))
    forger, registration = flows.registered(
        flows.Forger(events), actors, path="x/y.bin", kind="restricted_untracked_file"
    )
    source = {"identity_kind": "restricted_untracked_file", "path": "x/y.bin", "sha256": "a" * 64, "byte_length": 1}
    record = flows.observation(forger.project_id, actors.observer, flows.at(30), registration, pin, source=source)
    forger = forger.row("LR-015", record["record_id"], record, actor=actors.observer, when=flows.at(30))
    replay_legacy(forger.events, schemas=schemas, pinned_signatures=(pin,))


def test_a_w9_event_type_under_a_non_w9_command_is_refused(base) -> None:
    events, schemas = base
    ledger = _forge(events, "RegisterCandidate", "LegacyRecordObserved", _observation(_tracked()))
    with pytest.raises(IntegrityError, match="W9 event type under a non-W9 command"):
        replay_legacy(ledger, schemas=schemas)


def test_replay_refuses_a_second_genesis(base) -> None:
    events, schemas = base
    genesis = next(event for event in events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis")
    ledger = _forge(events, genesis["command_type"], genesis["event_type"], deepcopy(genesis["payload"]))
    with pytest.raises(IntegrityError, match="second W9 genesis"):
        replay_legacy(ledger, schemas=schemas)


def test_replay_refuses_a_genesis_payload_other_than_accepted(base) -> None:
    events, schemas = base
    tampered = [deepcopy(event) for event in events]
    genesis = next(event for event in tampered if event["command_type"] == "ImportAcceptedW9CatalogueGenesis")
    genesis["payload"]["requested_genesis_transaction_id"] = "w9-genesis-request-v2"
    with pytest.raises(IntegrityError, match="differs from the accepted identity"):
        replay_legacy(_rehash_events(tuple(tampered)), schemas=schemas)


def test_replay_refuses_a_w9_genesis_with_no_prior_w11_genesis(base) -> None:
    events, schemas = base
    genesis = [event for event in events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis"]
    with pytest.raises(IntegrityError, match="requires a prior W11 genesis"):
        replay_legacy(genesis, schemas=schemas)


def test_replay_reserves_the_external_refs_and_no_reader_dereferences_them(base) -> None:
    events, schemas = base
    state = replay_legacy(events, schemas=schemas)
    assert set(state["reserved_ids"]) == {ref["id"] for ref in RESERVED_EXTERNAL_REFS.values()}
    assert all(state["identities"][ref["id"]] == "reserved_external_ref" for ref in RESERVED_EXTERNAL_REFS.values())
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).resolve().parents[3] / "research_system").rglob("*.py")
    )
    for ref in RESERVED_EXTERNAL_REFS.values():
        assert source.count(ref["id"]) == 1, ref["id"]  # only the accepted_w9 literal


# --- The deferred rows' reducers through replay_legacy (design note §§7.4, 9; review F-2, F-3) -----------------------
#
# Every row is routed here, so each transaction reaches its reducer exactly as WP9.3 to WP9.6 will route it. The E:
# records are schema-valid and replay_legacy validates them. The W2 payloads carry only the fields assignment and the
# reducers read: their full W2 schemas are checked by the generic replay, which the C2 tests above exercise.

_HASH = "0" * 64


def _obj() -> str:
    return new_id("scope_definition")


def _ref(identity: str) -> dict[str, Any]:
    return {"id": identity, "record_revision": 1, "content_hash": _HASH}


def _row(ledger: tuple[dict[str, Any], ...], row_id: str, *payloads: dict[str, Any], **kwargs: Any) -> tuple:
    """Append one transaction executing ``row_id``: its accepted events in order, one payload each.

    ``event_types`` overrides the event list, for a row with a repeated slot (LR-020).
    """
    route = LEGACY_ROW_ROUTES[row_id]
    event_types = kwargs.get("event_types") or [slot.event_type for slot in route.events if not slot.repeated]
    members = [
        (
            event_type,
            payload,
            f"ars://core/event/{event_type}" if event_type in W2_EVENT_TYPES else "ars://core/event",
        )
        for event_type, payload in zip(event_types, payloads, strict=True)
    ]
    return _forge_transaction(ledger, route.command_type, members)


def _propose_decision(ledger: tuple, row_id: str, decision_id: str, *evidence: str) -> tuple:
    return _row(
        ledger, row_id, {"new_decision_id": decision_id, "governing_evidence_refs": [f"W9:{row_id}", *evidence]}
    )


def _resolve(row_id: str, decision_id: str) -> dict[str, Any]:
    return {"decision_id": decision_id, "governing_evidence_refs": [f"W9:{row_id}"]}


def _replay_all(ledger: tuple, schemas: Any) -> dict[str, Any]:
    return replay_legacy(ledger, schemas=schemas, routed_rows=ALL_ROWS)


def _owner(events: tuple) -> str:
    """The genesis actor, the harness owner."""
    return next(event for event in events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis")["actor_id"]


def _registered(events: tuple) -> tuple[tuple, dict[str, Any], str]:
    """LR-003 → LR-004 → LR-005: one recorded legacy_owned registration under its Decision (G5).

    WP9.3-1 routes these rows with their full replay checks (WP9.3 note §6.2), so the flow is built to them.
    """
    forger, record = flows.registered(flows.Forger(events), flows.Actors(owner=_owner(events)))
    return forger.events, record, record["registration_decision_ref"]["id"]


def _transition_record(registration_id: str, decision_id: str, from_mode: str, to_mode: str) -> dict[str, Any]:
    record = _transition(from_mode, to_mode, mapping=to_mode == "successor_owned")
    record.update(record_id=_obj(), subject_registration_ref=_ref(registration_id), decision_ref=_ref(decision_id))
    return flows.stamp(record)


def _transitioned(ledger: tuple, row_id: str, record: dict[str, Any], decision_id: str) -> tuple:
    """LR-050 → LR-053 → ``row_id``. The Decision names the transition it governs as evidence."""
    ledger = _row(ledger, "LR-050", record)
    ledger = _propose_decision(ledger, "LR-053", decision_id, record["record_id"])
    return _row(ledger, row_id, _resolve(row_id, decision_id), deepcopy(record))


def test_g5_a_resolved_record_is_bound_to_its_proposal_and_decision(base) -> None:
    events, schemas = base
    ledger, record, decision_id = _registered(events)
    state = _replay_all(ledger, schemas)
    assert state["records"]["legacy_path_registration"] == {record["record_id"]: record}
    assert state["proposals"][record["record_id"]]["recorded"] is True
    assert state["decisions"][decision_id]["resolve_row"] == "LR-005"
    # A Decision that is not a recovery Decision names what it governs without adding a graph edge (W9-T21).
    assert decision_id not in state["reference_edges"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda record, _: record.update(paper_root_ref={**record["paper_root_ref"], "content_hash": "1" * 64}),
            "differs from its open proposal",
        ),
        (lambda record, _: record.update(record_id=_obj()), "differs from its open proposal"),
        (lambda record, _: record.update(decision_ref=_ref(new_id("decision"))), "names another Decision"),
    ],
    ids=["other-content", "no-proposal", "other-decision"],
)
def test_g5_a_resolved_record_other_than_its_proposal_is_refused(base, mutate: Any, message: str) -> None:
    """G5's equality in ``_record_resolved``, on a row WP9.3 leaves with WP9.2's rules (LR-050 → LR-053 → LR-054).

    On WP9.3's own rows F-8's subject check refuses first (``test_w9_wp9_3_replay``), so a WP9.6 row reaches this one.
    """
    events, schemas = base
    ledger, registration, _ = _registered(events)
    decision_id = new_id("decision")
    record = _transition_record(registration["record_id"], decision_id, "legacy_owned", "successor_owned")
    ledger = _row(ledger, "LR-050", record)
    ledger = _propose_decision(ledger, "LR-053", decision_id, record["record_id"])
    recorded = deepcopy(record)
    mutate(recorded, decision_id)
    flows.stamp(recorded)
    ledger = _row(ledger, "LR-054", _resolve("LR-054", decision_id), recorded)
    with pytest.raises(IntegrityError, match=message):
        _replay_all(ledger, schemas)


def test_a_decision_is_resolved_only_under_its_own_family(base) -> None:
    events, schemas = base
    actors = flows.Actors(owner=_owner(events))
    forger = flows.Forger(events)
    record = flows.registration(forger.project_id, actors.analyst, flows.at(0))
    ledger = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=flows.at(0)).events
    decision_id = new_id("decision")
    ledger = _propose_decision(ledger, "LR-053", decision_id)
    ledger = _row(ledger, "LR-005", _resolve("LR-005", decision_id), record)
    with pytest.raises(IntegrityError, match="resolved under another Decision family"):
        _replay_all(ledger, schemas)


def test_w9_t5_ownership_moves_legacy_to_successor_to_closed(base) -> None:
    events, schemas = base
    ledger, registration, _ = _registered(events)
    registration_id = registration["record_id"]
    to_successor = _transition_record(registration_id, (first := new_id("decision")), "legacy_owned", "successor_owned")
    ledger = _transitioned(ledger, "LR-054", to_successor, first)
    to_closed = _transition_record(
        registration_id, (second := new_id("decision")), "successor_owned", "closed_reference"
    )
    ledger = _transitioned(ledger, "LR-055", to_closed, second)
    state = _replay_all(ledger, schemas)
    assert state["ownership"] == {registration_id: "closed_reference"}
    assert state["row_counts"]["LR-054"] == state["row_counts"]["LR-055"] == 1


@pytest.mark.parametrize(
    ("first", "second", "message"),
    [
        # A from_mode other than the registration's current mode (current-mode check).
        (("LR-054", "legacy_owned", "successor_owned"), ("LR-054", "legacy_owned", "successor_owned"), "current mode"),
        # An allowed W9 transition under a row that admits another direction (_ROW_DIRECTIONS).
        (None, ("LR-055", "legacy_owned", "closed_reference"), "differs from accepted LR-055"),
        # Closing a registration that never left legacy ownership, under LR-055.
        (None, ("LR-055", "successor_owned", "closed_reference"), "current mode"),
    ],
    ids=["stale-from-mode", "wrong-row-direction", "not-yet-successor"],
)
def test_w9_t5_an_ownership_transition_other_than_allowed_is_refused(base, first, second, message: str) -> None:
    events, schemas = base
    ledger, registration, _ = _registered(events)
    for step in (first, second):
        if step is None:
            continue
        row_id, from_mode, to_mode = step
        decision_id = new_id("decision")
        record = _transition_record(registration["record_id"], decision_id, from_mode, to_mode)
        ledger = _transitioned(ledger, row_id, record, decision_id)
    with pytest.raises(IntegrityError, match=message):
        _replay_all(ledger, schemas)


def test_lr_020_records_its_acceptance_and_its_ownership_transitions(base) -> None:
    """LR-020's ownership events validate against the ownership schema, not the acceptance schema of their row."""
    events, schemas = base
    ledger, registration, _ = _registered(events)
    decision_id = new_id("decision")
    acceptance = flows.stamp({**_acceptance(), "record_id": _obj(), "decision_ref": _ref(decision_id)})
    closure = _transition_record(registration["record_id"], decision_id, "legacy_owned", "closed_reference")
    ledger = _row(ledger, "LR-016", acceptance)
    ledger = _propose_decision(ledger, "LR-019", decision_id, acceptance["record_id"])
    ledger = _row(
        ledger,
        "LR-020",
        _resolve("LR-020", decision_id),
        deepcopy(acceptance),
        closure,
        event_types=[
            "DecisionResolved",
            "LegacyClosedReferenceAcceptanceRecorded",
            "LegacyOwnershipTransitionedRecorded",
        ],
    )
    state = _replay_all(ledger, schemas)
    assert state["ownership"] == {registration["record_id"]: "closed_reference"}
    assert closure["record_id"] in state["records"]["legacy_ownership_transitioned"]


_TRACKER = b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n"


def _inventory_flow(events: tuple, *, verdict: str = "approve", request_row: str = "LR-012", subject: Any = None):
    """A tracker registration, its LR-011 inventory proposal, and a review of the proposal: by default its
    reproduction review, LR-012 → LR-013. WP9.3-1 routes these rows with their full checks (WP9.3 note §6.2)."""
    actors = flows.Actors(owner=_owner(events))
    forger, tracker = flows.registered(flows.Forger(events), actors, path="tracker.md", role="legacy_coordination")
    segmented = _load_tool("w9_segmentation").segment(_TRACKER, "tracker_task_row")
    record = flows.inventory(forger.project_id, actors.observer, flows.at(20), tracker, segmented)
    forger = forger.row("LR-011", record["record_id"], record, actor=actors.observer, when=flows.at(20))
    review_id = record["independent_reproduction_ref"]["id"]
    request = flows.review_request(
        request_row,
        subject or record,
        review_id,
        actors.reproducer,
        flows.at(21),
        sessions=("session-analyst", "session-author") if request_row == "LR-007" else ("session-analyst",),
    )
    forger = forger.row(request_row, review_id, request, actor=actors.analyst, when=flows.at(21))
    answer = flows.verdict(
        request, flows.at(21), actors.reproducer, verdict_value=verdict, reviewer_session="session-reproducer"
    )
    forger = forger.row(
        verdict_row_for_request(request_row), review_id, answer, actor=actors.reproducer, when=flows.at(22)
    )
    return forger, record, actors


def test_lr_014_records_the_proposed_inventory_once_reproduced(base) -> None:
    """Review F-2: LR-014 records the LR-011 proposal under its own ID, claiming no second identity."""
    events, schemas = base
    forger, record, actors = _inventory_flow(events)
    forger = forger.row("LR-014", record["record_id"], deepcopy(record), actor=actors.observer, when=flows.at(23))
    state = _replay_all(forger.events, schemas)
    assert state["records"]["legacy_light_inventory"] == {record["record_id"]: record}
    assert state["proposals"][record["record_id"]]["recorded"] is True
    assert state["identities"][record["record_id"]] == "proposal"
    again = forger.row("LR-014", record["record_id"], deepcopy(record), actor=actors.observer, when=flows.at(24))
    with pytest.raises(IntegrityError, match="differs from its open proposal"):
        _replay_all(again.events, schemas)


@pytest.mark.parametrize(
    ("flow", "recorded", "message"),
    [
        (
            {},
            lambda record: flows.stamp({**record, "created_at": "2026-10-24T00:00:00Z"}),
            "differs from its open proposal",
        ),
        ({}, lambda record: flows.stamp({**record, "record_id": _obj()}), "differs from its open proposal"),
        ({"verdict": "changes_requested"}, dict, "no approved reproduction review"),
        # WP9.3-1: a request must name an open proposal of its row's kind (note §6.2, LR-012), so a review of another
        # subject, or a membership-row review of the inventory (review N-1), is refused at the request, before LR-014.
        (
            {"subject": {"record_id": "obj_01a17eb7-5ae0-7000-8000-0000000000ff", "content_hash": "0" * 64}},
            dict,
            "W9 step names no legacy_light_inventory proposal",
        ),
        ({"request_row": "LR-007"}, dict, "W9 step names no legacy_field_family_membership proposal"),
    ],
    ids=["other-bytes", "unbound-fresh-id", "not-approved", "review-of-another-subject", "not-a-reproduction-review"],
)
def test_lr_014_an_inventory_without_its_proposal_or_approval_is_refused(base, flow, recorded, message: str) -> None:
    events, schemas = base
    forger, record, actors = _inventory_flow(events, **flow)
    recorded_record = recorded(deepcopy(record))
    forger = forger.row(
        "LR-014", recorded_record["record_id"], recorded_record, actor=actors.observer, when=flows.at(23)
    )
    with pytest.raises(IntegrityError, match=message):
        _replay_all(forger.events, schemas)


def test_lr_014_reducer_refuses_an_approval_under_another_review_row() -> None:
    """Review N-1 at LR-014's own reducer, which a valid ledger now reaches only past the request checks."""
    state = reducers.new_legacy_state()
    record = {
        "schema_id": "ars://legacy/legacy-light-inventory",
        "record_id": "obj_a",
        "independent_reproduction_ref": {"id": "rev_a"},
    }
    record = flows.stamp(record)
    state["proposals"]["obj_a"] = {"kind": "legacy_light_inventory", "record": record, "recorded": False}
    state["reviews"]["rev_a"] = {
        "verdict_row": "LR-008",
        "verdict": "approve",
        "subjects": [("obj_a", record["content_hash"])],
    }
    transaction = [{"payload": record}]
    with pytest.raises(IntegrityError, match="no approved reproduction review"):
        reducers.reduce_light_inventory(state, "LR-099", transaction, {})
    state["reviews"]["rev_a"]["verdict_row"] = "LR-013"
    reducers.reduce_light_inventory(state, "LR-099", transaction, {})


def _root(predecessor_id: str | None = None, decision_id: str | None = None) -> dict[str, Any]:
    recovery = None
    if predecessor_id is not None:
        recovery = {"predecessor_root_ref": _ref(predecessor_id), "recovery_decision_ref": _ref(decision_id or "")}
    return flows.stamp({**_paper_root(), "record_id": _obj(), "recovery": recovery})


def _recovery(events: tuple, *, evidence: tuple[str, ...] = (), resolve: bool = True) -> tuple[tuple, dict, str]:
    """LR-035 → LR-036 → LR-037: an ordinary root and its resolved recovery Decision."""
    predecessor = _root()
    decision_id = new_id("decision")
    ledger = _row(events, "LR-035", predecessor)
    ledger = _propose_decision(ledger, "LR-036", decision_id, predecessor["record_id"], *evidence)
    if resolve:
        ledger = _row(ledger, "LR-037", _resolve("LR-037", decision_id))
    return ledger, predecessor, decision_id


def test_w9_t21_a_recovery_root_follows_its_resolved_recovery_decision(base) -> None:
    events, schemas = base
    ledger, predecessor, decision_id = _recovery(events)
    root = _root(predecessor["record_id"], decision_id)
    state = _replay_all(_row(ledger, "LR-038", root), schemas)
    assert set(state["records"]["legacy_paper_root"]) == {predecessor["record_id"], root["record_id"]}
    assert state["reference_edges"][decision_id] == [predecessor["record_id"]]


def test_w9_t21_a_recovery_decision_naming_its_recovery_root_is_refused(base) -> None:
    events, schemas = base
    root_id = _obj()
    ledger, predecessor, decision_id = _recovery(events, evidence=(root_id,))
    root = flows.stamp({**_root(predecessor["record_id"], decision_id), "record_id": root_id})
    with pytest.raises(IntegrityError, match="W9 recovery Decision names its recovery root"):
        _replay_all(_row(ledger, "LR-038", root), schemas)


def test_w9_t21_a_recovery_root_needs_a_resolved_decision_and_a_recorded_predecessor(base) -> None:
    events, schemas = base
    ledger, predecessor, decision_id = _recovery(events, resolve=False)
    with pytest.raises(IntegrityError, match="names no resolved recovery Decision"):
        _replay_all(_row(ledger, "LR-038", _root(predecessor["record_id"], decision_id)), schemas)
    ledger, _, decision_id = _recovery(events)
    with pytest.raises(IntegrityError, match="names no recorded predecessor root"):
        _replay_all(_row(ledger, "LR-038", _root(_obj(), decision_id)), schemas)


def test_w9_t21_a_cycle_through_a_root_a_transition_and_a_recovery_decision_is_refused(base) -> None:
    """The recovery Decision names a transition, the transition names the recovery root, the root names the Decision."""
    events, schemas = base
    ledger, registration, _ = _registered(events)
    transition_decision = new_id("decision")
    transition = _transition_record(registration["record_id"], transition_decision, "legacy_owned", "successor_owned")
    ledger, predecessor, recovery_decision = _recovery(ledger, evidence=(transition["record_id"],))
    root = _root(predecessor["record_id"], recovery_decision)
    ledger = _row(ledger, "LR-038", root)
    transition["paper_root_ref"] = _ref(root["record_id"])
    flows.stamp(transition)
    ledger = _transitioned(ledger, "LR-054", transition, transition_decision)
    with pytest.raises(IntegrityError, match="W9 reference cycle"):
        _replay_all(ledger, schemas)


def _supersession(superseded: str, replacing: str, decision_id: str) -> dict[str, Any]:
    return flows.stamp(
        {
            **_header("legacy-record-supersession"),
            "record_id": _obj(),
            "superseded_ref": _ref(superseded),
            "replacing_ref": _ref(replacing),
            "reason": "test supersession",
            "reviewer_ref": _ref(new_id("review")),
            "decision_ref": _ref(decision_id),
        }
    )


def _superseded(ledger: tuple, superseded: str, replacing: str) -> tuple:
    """LR-056 → LR-059 → LR-060."""
    decision_id = new_id("decision")
    record = _supersession(superseded, replacing, decision_id)
    ledger = _row(ledger, "LR-056", record)
    ledger = _propose_decision(ledger, "LR-059", decision_id, record["record_id"])
    return _row(ledger, "LR-060", _resolve("LR-060", decision_id), deepcopy(record))


def test_supersession_through_lr_060_is_acyclic(base) -> None:
    """Two recorded paper roots (LR-035) supersede each other: once, then never back (WP9.3 note §3 row 5)."""
    events, schemas = base
    first, second = _root(), _root()
    ledger = _row(_row(events, "LR-035", first), "LR-035", second)
    first, second = first["record_id"], second["record_id"]
    ledger = _superseded(ledger, first, second)
    assert _replay_all(ledger, schemas)["supersessions"] == {first: second}
    with pytest.raises(IntegrityError, match="W9 supersession cycle"):
        _replay_all(_superseded(ledger, second, first), schemas)


def test_supersession_of_a_record_that_does_not_exist_is_refused(base) -> None:
    """WP9.3 note §3 row 5: replay refuses a superseded ref naming no recorded record, with WP9.6's rows routed."""
    events, schemas = base
    replacing = _root()
    ledger = _row(events, "LR-035", replacing)
    with pytest.raises(IntegrityError, match="W9 supersession names no recorded record"):
        _replay_all(_superseded(ledger, _obj(), replacing["record_id"]), schemas)
