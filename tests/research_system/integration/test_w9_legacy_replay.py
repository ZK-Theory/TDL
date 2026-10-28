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

import research_system.legacy.commands as legacy_commands
import research_system.legacy.replay.driver as legacy_driver
import research_system.schema_registry as registry_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy.accepted_w9 import RESERVED_EXTERNAL_REFS
from research_system.legacy.replay.driver import replay_legacy
from research_system.projection.replay import _validate_active_lifecycle_binding, rebuild_projection
from research_system.projection.replay import replay as replay_projection
from research_system.schema_registry import SchemaBinding
from tests.research_system.contracts.test_w9_contract_materialization import _observation, _tracked
from tests.research_system.integration.test_w9_legacy_runtime import _genesis_command, _store
from tests.research_system.integration.test_wp6_6_discovery_runtime import _rehash_events

SCHEMA_ROOT = Path(registry_module.__file__).resolve().parent.parent / ".research-system" / "schemas"
W9_BINDINGS = tuple(
    SchemaBinding("ars://core/command", "1.0.0", command_type=name)
    for name in sorted(legacy_commands.LEGACY_COMMAND_TYPES - {"ImportAcceptedW9CatalogueGenesis"})
)
REVIEW_PRODUCER = SchemaBinding(
    "ars://core/event/ReviewRequested",
    "1.0.0",
    event_type="ReviewRequested",
    producer_command_type="RequestW9AuthorityReview",
)
TEST_ROUTES = frozenset({"LR-001", "LR-007", "LR-015"})


def _registry(monkeypatch: pytest.MonkeyPatch, extra: tuple[SchemaBinding, ...] = ()) -> Any:
    monkeypatch.setattr(registry_module, "_RUNTIME_BINDINGS", (*registry_module._RUNTIME_BINDINGS, *extra))
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


def _forge(
    events: tuple[dict[str, Any], ...],
    command_type: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    schema_id: str = "ars://core/event",
) -> tuple[dict[str, Any], ...]:
    template = next(event for event in events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis")
    event = deepcopy(template)
    command_id = new_id("command")
    event.update(
        {
            "event_id": new_id("event"),
            "global_position": len(events) + 1,
            "stream_id": new_id("scope_definition"),
            "stream_version": 1,
            "transaction_id": new_id("event_batch"),
            "transaction_index": 1,
            "transaction_count": 1,
            "command_id": command_id,
            "command_type": command_type,
            "event_type": event_type,
            "schema_id": schema_id,
            "schema_version": "1.0.0",
            "idempotency_key": f"w9-test:{command_id}",
            "command_payload_hash": sha256_hex(canonical_bytes(payload)),
            "correlation_id": command_id,
            "payload": payload,
        }
    )
    return _rehash_events((*events, event))


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
    events, _ = base
    schemas = _registry(monkeypatch, (*W9_BINDINGS, REVIEW_PRODUCER))
    _route(monkeypatch)
    ledger = _forge(
        _observed(events),
        "RequestW9AuthorityReview",
        "ReviewRequested",
        _review_request(),
        schema_id="ars://core/event/ReviewRequested",
    )
    replay_projection(ledger, schema_registry=schemas)
    rebuild_projection(ledger, tmp_path / "projection.json", schemas)
    replay_discovery(ledger, schemas=schemas)
    state = replay_legacy(ledger, schemas=schemas, routed_rows=TEST_ROUTES)
    assert state["row_counts"] == {"LR-001": 1, "LR-015": 1, "LR-007": 1}


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
    schemas = _registry(monkeypatch, (*W9_BINDINGS, REVIEW_PRODUCER))
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
    events, _ = base
    schemas = _registry(monkeypatch)
    _route(monkeypatch)
    with pytest.raises(IntegrityError, match="schema provenance mismatch|command schema identity|binding"):
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
    events, _ = base
    schemas = _registry(monkeypatch, W9_BINDINGS)
    _route(monkeypatch)
    ledger = _forge(events, "RequestW9AuthorityReview", "ReviewRequested", _review_request(), schema_id=schema_id)
    with pytest.raises(IntegrityError) as refused:
        replay_discovery(ledger, schemas=schemas)
    assert message in f"{refused.value} {refused.value.__cause__}"


def test_c2_a_w2_typed_event_recorded_as_core_event_is_refused(base, monkeypatch) -> None:
    events, _ = base
    schemas = _registry(monkeypatch, (*W9_BINDINGS, REVIEW_PRODUCER))
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
    events, schemas = base
    with pytest.raises(IntegrityError, match=r"W9 row not routed in this version: LR-015 \(WP9.3\)"):
        replay_legacy(_observed(events), schemas=schemas)


def test_a_schema_invalid_payload_is_refused(base) -> None:
    events, schemas = base
    record = _observation(_tracked())
    del record["observer_actor_id"]
    with pytest.raises(IntegrityError, match="does not validate against its record schema"):
        replay_legacy(_observed(events, record), schemas=schemas, routed_rows=TEST_ROUTES)


def test_a_restricted_source_without_a_frozen_copy_replays(base) -> None:
    """The schema refuses a restricted source with a frozen copy before the reducer; the reducer half is unit-tested."""
    events, schemas = base
    record = _observation(
        {"identity_kind": "restricted_untracked_file", "path": "x/y.bin", "sha256": "a" * 64, "byte_length": 1}
    )
    replay_legacy(_observed(events, record), schemas=schemas, routed_rows=TEST_ROUTES)


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
