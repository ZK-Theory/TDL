# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-2 §10; P-081 item 5)
# Purpose: WP9.3-2's replay half on forged scratch ledgers: LR-016 to LR-020, the batch rules, pilot_promotion and the
# derived ownership list (owner point E).
"""WP9.3-2 replay controls (WP9.3 note §6.2, §10, §14, §17).

The base ledger is a scratch store holding W11 genesis and a real W9 genesis, carried through WP9.3-1's full flow (two
registrations, a membership table, an inventory and three observations). Each negative control changes one thing in an
otherwise valid acceptance flow and asserts the refusing check's own message, so it reaches the guard itself (§17). The
ownership records the tests expect are built by ``w9_flows.ownership_transition`` from §10.5's text, never by the
reducer that derives them.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import research_system.legacy.accepted_w9 as accepted_w9
from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy.replay import reducers
from research_system.legacy.replay.driver import apply_transaction, replay_legacy
from research_system.legacy.routes import LEGACY_ROUTED_ROWS
from research_system.projection.replay import rebuild_projection
from research_system.projection.replay import replay as replay_projection
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_wp9_3_replay import PIN, _full_flow
from tests.research_system.integration.test_w9_wp9_3_replay import base as base  # noqa: F401  (module fixture)
from tests.research_system.integration.w9_flows import Actors, Forger, Tweak, at

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture
def actors() -> Actors:
    from tests.research_system.factories import ACTORS

    return Actors(owner=ACTORS["actor-a"])


@pytest.fixture
def flow(base, actors) -> tuple[Forger, dict[str, dict[str, Any]], Any]:  # noqa: F811
    forger, records = _full_flow(base[0], actors)
    return forger, records, base[1]


def _replay(forger: Forger, schemas: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("pinned_signatures", (PIN,))
    return replay_legacy(forger.events, schemas=schemas, **kwargs)


def _refused(forger: Forger, schemas: Any, message: str, **kwargs: Any) -> None:
    with pytest.raises(IntegrityError, match=message):
        _replay(forger, schemas, **kwargs)


def _batch(forger: Forger, actors: Actors, *observations: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return flows.acceptance(forger.project_id, actors.analyst, at(60), list(observations), **overrides)


# --- The positive flow ------------------------------------------------------------------------------------------------


def test_an_accepted_first_batch_replays_and_closes_the_whole_file_registration(
    flow, actors, monkeypatch, tmp_path: Path
) -> None:
    """Note §17's whole-flow row, WP9.3-2 part: one accepted batch, through every public replay."""
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"], records["item"])
    expected = [flows.ownership_transition(record, records["registration"])]
    forger = flows.acceptance_recorded(forger, actors, record, expected)
    monkeypatch.setattr(accepted_w9, "ACCEPTED_W0_SIGNATURES", (PIN,))
    replay_projection(forger.events, schema_registry=schemas)
    rebuild_projection(forger.events, tmp_path / "projection.json", schemas)
    replay_discovery(forger.events, schemas=schemas)
    state = replay_legacy(forger.events, schemas=schemas)
    assert state["records"][reducers.ACCEPTANCE] == {record["record_id"]: record}
    # LR-020's ownership events validate against the ownership schema, not the acceptance schema of their row.
    assert state["records"][reducers.OWNERSHIP] == {expected[0]["record_id"]: expected[0]}
    assert state["ownership"] == {records["registration"]["record_id"]: "closed_reference"}
    assert state["proposals"][record["record_id"]]["ownership"] == expected
    for row in ("LR-016", "LR-017", "LR-018", "LR-019", "LR-020"):
        assert state["row_counts"][row] == 1
    for ref_id in (record["independent_review_ref"]["id"], record["decision_ref"]["id"], expected[0]["record_id"]):
        assert state["reservations"][ref_id]["used"] is True


def test_the_ownership_derivation_is_deterministic_and_distinct_across_batches(flow, actors) -> None:
    forger, records, schemas = flow
    state = _replay(forger, schemas)
    first = _batch(forger, actors, records["whole"])
    second = _batch(forger, actors, records["whole"])
    assert reducers.derive_ownership(state, first) == reducers.derive_ownership(state, first)
    assert reducers.derive_ownership(state, first) == [flows.ownership_transition(first, records["registration"])]
    ids = {reducers.derive_ownership(state, batch)[0]["record_id"] for batch in (first, second)}
    assert len(ids) == 2


def test_a_whole_file_item_of_a_registration_not_legacy_owned_transitions_nothing(base, actors) -> None:  # noqa: F811
    """§10.5: only a legacy_owned registration transitions (LR-020's one direction, P-072 item 2)."""
    forger, registration = flows.registered(base[0], actors, ownership_mode="successor_owned")
    whole = flows.observation(forger.project_id, actors.observer, at(50), registration, PIN)
    forger = forger.row("LR-015", whole["record_id"], whole, actor=actors.observer, when=at(50))
    state = _replay(forger, base[1])
    assert reducers.derive_ownership(state, _batch(forger, actors, whole)) == []


def test_an_inventory_item_and_a_partial_family_set_transition_nothing(flow, actors) -> None:
    """§10.5: only an item covering the whole file transitions its registration."""
    forger, records, schemas = flow
    state = _replay(forger, schemas)
    assert reducers.derive_ownership(state, _batch(forger, actors, records["item"], records["family_set"])) == []


# --- LR-016: the batch rules (§10.1) ----------------------------------------------------------------------------------


def _at_lr016(forger: Forger, actors: Actors, record: dict[str, Any]) -> Forger:
    return flows.acceptance_recorded(forger, actors, record, [], stop_after="LR-016")


def test_lr016_refuses_an_observation_named_twice(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    twice = {**deepcopy(record["items"][0]), "pilot_promotion": [*flows.pilot_promotion(), *[]]}
    twice["pilot_promotion"].append({"fixture_id": "F-017", "disposition": "evidence", "ref": flows.evidence_ref()})
    record = flows.stamp({**record, "items": [record["items"][0], twice]})
    _refused(_at_lr016(forger, actors, record), schemas, "W9 acceptance batch names an observation twice")


def test_lr016_refuses_more_than_the_batch_limit(flow, actors, monkeypatch) -> None:
    """The limit is 20 (§10.1). Building 21 observations is not needed to reach the guard: the bound is lowered to 1
    for the test, and a two-item batch meets the same predicate."""
    forger, records, schemas = flow
    monkeypatch.setattr(reducers, "MAX_BATCH_ITEMS", 1)
    record = _batch(forger, actors, records["whole"], records["item"])
    _refused(_at_lr016(forger, actors, record), schemas, "W9 acceptance batch must hold 1 to 20 items")
    assert reducers.MAX_BATCH_ITEMS == 1  # the real value is pinned below


def test_the_batch_limit_is_twenty() -> None:
    assert reducers.MAX_BATCH_ITEMS == 20


def test_lr016_refuses_a_stale_observation(flow, actors) -> None:
    forger, records, schemas = flow
    later = flows.observation(
        forger.project_id,
        actors.observer,
        at(55),
        records["registration"],
        PIN,
        count=2,
        source=flows.tracked(sha256="b" * 64, blob="2" * 40),
    )
    forger = forger.row("LR-015", later["record_id"], later, actor=actors.observer, when=at(55))
    assert records["whole"]["record_id"] in _replay(forger, schemas)["stale_observations"]
    _refused(
        _at_lr016(forger, actors, _batch(forger, actors, records["whole"])),
        schemas,
        "W9 acceptance item's observation is stale",
    )


def test_lr016_refuses_an_observation_that_is_not_the_latest_for_its_source_and_selector(flow, actors) -> None:
    forger, records, schemas = flow
    again = flows.observation(forger.project_id, actors.observer, at(55), records["registration"], PIN, count=2)
    forger = forger.row("LR-015", again["record_id"], again, actor=actors.observer, when=at(55))
    assert records["whole"]["record_id"] not in _replay(forger, schemas)["stale_observations"]
    _refused(
        _at_lr016(forger, actors, _batch(forger, actors, records["whole"])),
        schemas,
        "W9 acceptance item's observation is not the latest for its source and selector",
    )


def test_lr016_compares_family_set_selectors_as_sets(flow, actors) -> None:
    """A later observation naming the same families in another order replaces the earlier one (CodeRabbit, #432)."""
    forger, records, schemas = flow
    names = [family["name"] for family in records["table"]["families"]]
    assert len(names) >= 2

    def complete(order: list[str], count: int, minute: int) -> dict[str, Any]:
        return flows.observation(
            forger.project_id,
            actors.observer,
            at(minute),
            records["registration"],
            PIN,
            count=count,
            selector={
                "selector_kind": "json_family_set",
                "membership_ref": flows.record_ref(records["table"]),
                "family_names": order,
            },
            families=[flows.signed_family(name, PIN) for name in order],
        )

    earlier, later = complete(names, 2, 55), complete(list(reversed(names)), 3, 56)
    forger = forger.row("LR-015", earlier["record_id"], earlier, actor=actors.observer, when=at(55))
    forger = forger.row("LR-015", later["record_id"], later, actor=actors.observer, when=at(56))
    assert earlier["record_id"] not in _replay(forger, schemas)["stale_observations"]
    _refused(
        _at_lr016(forger, actors, _batch(forger, actors, earlier)),
        schemas,
        "W9 acceptance item's observation is not the latest for its source and selector",
    )


def test_lr016_refuses_two_whole_file_items_of_one_registration(flow, actors) -> None:
    """§10.5 (review m-2): a whole_file item and a complete family set of the same registration."""
    forger, records, schemas = flow
    names = [family["name"] for family in records["table"]["families"]]
    complete = flows.observation(
        forger.project_id,
        actors.observer,
        at(55),
        records["registration"],
        PIN,
        count=2,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(records["table"]),
            "family_names": names,
        },
        families=[flows.signed_family(name, PIN) for name in names],
    )
    forger = forger.row("LR-015", complete["record_id"], complete, actor=actors.observer, when=at(55))
    _refused(
        _at_lr016(forger, actors, _batch(forger, actors, records["whole"], complete)),
        schemas,
        "W9 acceptance batch holds two whole-file items of one registration",
    )


def test_lr016_refuses_a_batch_after_a_recorded_acceptance(flow, actors) -> None:
    """§2.1, §10.1: the first batch only, until WP9.7 routes LR-022."""
    forger, records, schemas = flow
    first = _batch(forger, actors, records["whole"])
    forger = flows.acceptance_recorded(
        forger, actors, first, [flows.ownership_transition(first, records["registration"])]
    )
    second = flows.acceptance(forger.project_id, actors.analyst, at(70), [records["item"]])
    _refused(
        flows.acceptance_recorded(forger, actors, second, [], start=70, stop_after="LR-016"),
        schemas,
        "W9 acceptance after the first batch needs the integration-pilot outcome Decision",
    )


def test_lr016_refuses_an_ars_event_anchor(flow, actors) -> None:
    """Owner point G: git_commit anchors only in v1."""
    forger, records, schemas = flow
    anchors = [
        {"anchored": "threshold_preregistration", "anchor_kind": "ars_event", "value": new_id("event")},
        {"anchored": "governing_record_set", "anchor_kind": "git_commit", "value": flows.SHA1},
    ]
    record = _batch(forger, actors, records["whole"], anchors=anchors)
    _refused(
        _at_lr016(forger, actors, record),
        schemas,
        r"W9 acceptance anchor must be a git_commit anchor \(owner point G\)",
    )


def test_lr016_refuses_a_null_change_list(flow, actors) -> None:
    """§10.4: the schema's null is never accepted in v1."""
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    record = flows.stamp({**record, "enforcement_change_list": None})
    _refused(_at_lr016(forger, actors, record), schemas, "W9 acceptance names no shared-surface change list")


def test_check_acceptance_requires_genesis_and_a_pinned_signature(flow, actors) -> None:
    """Defence in depth: on a real ledger LR-015 already needs both, so the predicate is called directly."""
    forger, records, schemas = flow
    state = _replay(forger, schemas)
    record = _batch(forger, actors, records["whole"])
    with pytest.raises(IntegrityError, match="W9 acceptance requires a pinned W0 signature"):
        reducers.check_acceptance(state, record, {"pinned_signatures": ()})
    with pytest.raises(IntegrityError, match="W9 acceptance requires W9 genesis"):
        reducers.check_acceptance({**state, "catalogue": None}, record, {"pinned_signatures": (PIN,)})
    reducers.check_acceptance(state, record, {"pinned_signatures": (PIN,)})


# --- LR-016: pilot_promotion (§10.2, O-37) ----------------------------------------------------------------------------


def _with_pilot(forger: Forger, actors: Actors, records: dict[str, Any], entries: list[dict[str, Any]]) -> Forger:
    record = _batch(forger, actors, records["whole"])
    record = flows.stamp({**record, "items": [{**record["items"][0], "pilot_promotion": entries}]})
    return _at_lr016(forger, actors, record)


@pytest.mark.parametrize("fixture", flows.UNCONDITIONAL_FIXTURES)
def test_lr016_refuses_an_item_missing_an_unconditional_fixture(flow, actors, fixture: str) -> None:
    forger, records, schemas = flow
    entries = [entry for entry in flows.pilot_promotion() if entry["fixture_id"] != fixture]
    _refused(
        _with_pilot(forger, actors, records, entries),
        schemas,
        f"W9 acceptance item lacks the unconditional fixture {fixture}",
    )


def test_lr016_refuses_a_fixture_listed_twice(flow, actors) -> None:
    forger, records, schemas = flow
    entries = [
        *flows.pilot_promotion(),
        {"fixture_id": "S-014", "disposition": "evidence", "ref": flows.evidence_ref()},
    ]
    _refused(_with_pilot(forger, actors, records, entries), schemas, "W9 acceptance item lists a fixture twice")


def test_lr016_refuses_a_fixture_outside_lr020s_seven(flow, actors) -> None:
    """The plan's Q2 (Stephen, 2026-11-11): a fixture LR-020 does not name is refused."""
    forger, records, schemas = flow
    entries = [
        *flows.pilot_promotion(),
        {"fixture_id": "F-001", "disposition": "evidence", "ref": flows.evidence_ref()},
    ]
    _refused(
        _with_pilot(forger, actors, records, entries),
        schemas,
        "W9 acceptance item lists a fixture LR-020 does not name: F-001",
    )


def test_lr016_admits_each_conditional_fixture(flow, actors) -> None:
    forger, records, schemas = flow
    entries = [
        *flows.pilot_promotion(),
        *(
            {"fixture_id": f, "disposition": "evidence", "ref": flows.evidence_ref()}
            for f in ("F-017", "S-005", "F-038")
        ),
    ]
    _replay(_with_pilot(forger, actors, records, entries), schemas)


def test_lr016_refuses_an_evidence_ref_of_the_wrong_kind(flow, actors) -> None:
    forger, records, schemas = flow
    entries = flows.pilot_promotion(
        F_018={"fixture_id": "F-018", "disposition": "evidence", "ref": flows.evidence_ref("scope_definition")}
    )
    _refused(
        _with_pilot(forger, actors, records, entries),
        schemas,
        "W9 pilot_promotion evidence ref must be a review or an artefact",
    )


def test_an_evidence_ref_may_name_an_artefact_and_a_waiver_a_decision(flow, actors) -> None:
    forger, records, schemas = flow
    entries = flows.pilot_promotion(
        F_018={"fixture_id": "F-018", "disposition": "evidence", "ref": flows.evidence_ref("artefact")},
        S_014={"fixture_id": "S-014", "disposition": "waiver", "ref": flows.evidence_ref("decision")},
    )
    _replay(_with_pilot(forger, actors, records, entries), schemas)


def test_a_waiver_ref_that_is_not_a_decision_is_refused_by_the_predicate() -> None:
    """The schema already refuses it (a waiver's ref is a decisionRef), so the predicate is called directly."""
    entries = flows.pilot_promotion(S_014={"fixture_id": "S-014", "disposition": "waiver", "ref": flows.evidence_ref()})
    with pytest.raises(IntegrityError, match="W9 pilot_promotion waiver ref must be a Decision"):
        reducers._check_pilot_promotion({"pilot_promotion": entries})


# --- LR-017 to LR-019 -------------------------------------------------------------------------------------------------


def test_lr017_refuses_a_reviewer_who_observed_an_item_of_the_batch(flow, actors) -> None:
    """§5.5, §6.2 LR-017 (G3, W9-C20)."""
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    tweak = Tweak(payload={"reviewer_capability": [actors.observer]})
    forged = flows.acceptance_recorded(forger, actors, record, [], tweaks={"LR-017": tweak}, stop_after="LR-017")
    _refused(forged, schemas, "W9 acceptance reviewer observed an item of the batch")


def test_lr017_refuses_a_reviewer_who_proposed_the_batch(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    tweak = Tweak(payload={"reviewer_capability": [actors.analyst]})
    forged = flows.acceptance_recorded(forger, actors, record, [], tweaks={"LR-017": tweak}, stop_after="LR-017")
    _refused(forged, schemas, "W9 reviewer is the proposal's creator, author or the requesting analyst")


def test_lr017_admits_the_batchs_analyst_as_the_requester(flow, actors) -> None:
    """Reading R8: the batch is the analyst's own proposal, as a path registration is."""
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    _replay(flows.acceptance_recorded(forger, actors, record, [], stop_after="LR-017"), schemas)


def test_lr018_refuses_a_verdict_from_the_analysts_session(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    tweak = Tweak(payload={"reviewer_session": "session-analyst"})
    forged = flows.acceptance_recorded(forger, actors, record, [], tweaks={"LR-018": tweak}, stop_after="LR-018")
    _refused(forged, schemas, "W9 reviewer session is a session the request records")


def test_lr019_refuses_a_decision_without_an_approved_review(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    tweak = Tweak(payload={"verdict": "changes_requested"})
    forged = flows.acceptance_recorded(forger, actors, record, [], tweaks={"LR-018": tweak}, stop_after="LR-019")
    _refused(forged, schemas, "W9 Decision proposal has no satisfied review on the current hash")


# --- LR-020: G5 and the ownership list (§6.1, §10.5, §10.6) -----------------------------------------------------------


def _expected(records: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    return [flows.ownership_transition(record, records["registration"])]


def test_lr020_refuses_an_omitted_ownership_record(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    forged = flows.acceptance_recorded(forger, actors, record, _expected(records, record), emitted=[])
    _refused(forged, schemas, "W9 acceptance's ownership records differ from the list stored at LR-016")


def test_lr020_refuses_an_added_ownership_record(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    expected = _expected(records, record)
    extra = flows.ownership_transition(record, records["tracker"])
    forged = flows.acceptance_recorded(forger, actors, record, expected, emitted=[*expected, extra])
    _refused(forged, schemas, "W9 acceptance's ownership records differ from the list stored at LR-016")


def test_lr020_refuses_an_altered_ownership_record(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    expected = _expected(records, record)
    altered = flows.stamp({**deepcopy(expected[0]), "created_by_actor_id": actors.reviewer})
    forged = flows.acceptance_recorded(forger, actors, record, expected, emitted=[altered])
    _refused(forged, schemas, "W9 acceptance's ownership records differ from the list stored at LR-016")


def test_lr020_refuses_reordered_ownership_records(flow, actors) -> None:
    forger, records, schemas = flow
    tracker_whole = flows.observation(forger.project_id, actors.observer, at(55), records["tracker"], PIN, count=1)
    forger = forger.row("LR-015", tracker_whole["record_id"], tracker_whole, actor=actors.observer, when=at(55))
    record = _batch(forger, actors, records["whole"], tracker_whole)
    expected = [
        flows.ownership_transition(record, records["registration"]),
        flows.ownership_transition(record, records["tracker"]),
    ]
    _replay(flows.acceptance_recorded(forger, actors, record, expected), schemas)
    forged = flows.acceptance_recorded(forger, actors, record, expected, emitted=expected[::-1])
    _refused(forged, schemas, "W9 acceptance's ownership records differ from the list stored at LR-016")


def test_lr020_refuses_an_ownership_record_whose_copied_refs_are_not_the_acceptances(flow, actors) -> None:
    """§4.2, §10.6: the copied refs are the acceptance's, pre-assigned hashes included."""
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    expected = _expected(records, record)
    other = flows.pre_assigned_ref("review", record["independent_review_ref"]["id"], new_id("scope_definition"))
    altered = flows.stamp({**deepcopy(expected[0]), "reviewer_ref": other})
    forged = flows.acceptance_recorded(forger, actors, record, expected, emitted=[altered])
    _refused(forged, schemas, "W9 ownership record's copied refs are not the acceptance's")


def test_lr020_refuses_an_ownership_record_off_its_own_streams_first_version(flow, actors) -> None:
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    expected = _expected(records, record)
    base_forger = flows.acceptance_recorded(forger, actors, record, expected, stop_after="LR-019")
    events = list(flows.acceptance_recorded(forger, actors, record, expected).events)
    events[-1] = {**events[-1], "stream_version": 2}
    from tests.research_system.integration.test_wp6_6_discovery_runtime import _rehash_events

    forged = Forger(_rehash_events(tuple(events)))
    assert len(forged.events) == len(base_forger.events) + 3
    _refused(forged, schemas, "W9 ownership record is not at its own stream's version 1")


def test_lr020_refuses_a_list_recomputed_differently_from_the_stored_one(flow, actors) -> None:
    """The recompute guard is reached only when the emitted records equal the stored list but the projection no longer
    derives it; on a real ledger nothing can change it between LR-016 and LR-020, so the stored list is changed in the
    replayed state and LR-020 applied through the driver's own per-transaction step."""
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    expected = _expected(records, record)
    before = flows.acceptance_recorded(forger, actors, record, expected, stop_after="LR-019")
    full = flows.acceptance_recorded(forger, actors, record, expected)
    state = _replay(before, schemas)
    changed = flows.stamp({**deepcopy(expected[0]), "created_by_actor_id": actors.reviewer})
    state["proposals"][record["record_id"]]["ownership"] = [changed]
    transaction = [deepcopy(event) for event in full.events[len(before.events) :]]
    transaction[-1]["payload"] = changed
    with pytest.raises(IntegrityError, match="W9 acceptance's ownership list recomputed at LR-020 differs"):
        apply_transaction(
            state, transaction, schemas=schemas, routed_rows=LEGACY_ROUTED_ROWS, context={"pinned_signatures": (PIN,)}
        )


def test_two_batches_sharing_an_item_cannot_both_resolve(flow, actors) -> None:
    """Review M-1 (note §10.1): both proposed and reviewed before either resolves; the second resolution refused."""
    forger, records, schemas = flow
    first = _batch(forger, actors, records["whole"])
    second = flows.acceptance(forger.project_id, actors.analyst, at(70), [records["whole"], records["item"]])
    forger = flows.acceptance_recorded(forger, actors, first, [], stop_after="LR-019")
    forger = flows.acceptance_recorded(forger, actors, second, [], start=70, stop_after="LR-019")
    grant = new_id("authority_grant")
    for record, when in ((first, at(80)), (second, at(81))):
        proposal = flows.decision_proposal(
            "LR-019", record, record["decision_ref"]["id"], at(63 if record is first else 73)
        )
        resolved = flows.resolution(
            "LR-020", proposal, record, actors.owner, grant, when, [record["independent_review_ref"]["id"]]
        )
        members = [
            ("DecisionResolved", record["decision_ref"]["id"], resolved),
            ("LegacyClosedReferenceAcceptanceRecorded", record["record_id"], deepcopy(record)),
            *(
                ("LegacyOwnershipTransitionedRecorded", t["record_id"], t)
                for t in [flows.ownership_transition(record, records["registration"])]
            ),
        ]
        forger = forger.append("ResolveW9AuthorityDecision", members, actor=actors.owner, when=when, grant=grant)
        if record is first:
            _replay(forger, schemas)
    _refused(forger, schemas, "W9 acceptance after the first batch needs the integration-pilot outcome Decision")


def test_an_ownership_id_reserved_at_lr016_cannot_be_claimed_by_another_record(flow, actors) -> None:
    """§4.3: the batch's ownership IDs are reserved at LR-016."""
    forger, records, schemas = flow
    record = _batch(forger, actors, records["whole"])
    expected = _expected(records, record)
    forger = flows.acceptance_recorded(forger, actors, record, expected, stop_after="LR-016")
    squatter = flows.stamp(
        {
            **flows.registration(forger.project_id, actors.analyst, at(62), path="other.json"),
            "record_id": expected[0]["record_id"],
        }
    )
    squatter["registration_decision_ref"] = flows.pre_assigned_ref(
        "decision", new_id("decision"), squatter["record_id"]
    )
    squatter = flows.stamp(squatter)
    forged = forger.row("LR-003", squatter["record_id"], squatter, actor=actors.analyst, when=at(62))
    _refused(forged, schemas, "W9 identity collision")
