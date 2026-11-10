# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1; P-080, P-081)
# Purpose: WP9.3-1's replay half on forged scratch ledgers: LR-003 to LR-015, N-2, identities, W2 encodings, lapse.
"""WP9.3-1 replay controls (WP9.3 note §4 to §9, §14, §17).

The base ledger is a scratch store holding W11 genesis and a real W9 genesis. Every flow is forged onto a copy and
re-hashed; nothing is written back. Each negative control changes one field of an otherwise valid flow and asserts the
refusing check's own message, so it reaches the guard itself (note §17).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import research_system.legacy.accepted_w9 as accepted_w9
from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy.accepted_w9 import CATALOGUE_STREAM_ID, RESERVED_IDS
from research_system.legacy.records import pre_assigned_ref, record_content_hash
from research_system.legacy.replay.driver import replay_legacy
from research_system.projection.replay import rebuild_projection
from research_system.projection.replay import replay as replay_projection
from tests.research_system.contracts.test_w9_contract_materialization import _load_tool
from tests.research_system.factories import ACTORS
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_legacy_runtime import _genesis_command, _store
from tests.research_system.integration.w9_flows import Actors, Forger, at

OWNER = ACTORS["actor-a"]
PIN = flows.signature()
SEGMENTER = _load_tool("w9_segmentation")
TRACKER = b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n| 1.2 | b |\n"
SOURCE_SHA = "a" * 64


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> tuple[Forger, Any]:
    tmp_path = tmp_path_factory.mktemp("w9-wp9-3-replay")
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    return Forger(tuple(harness.ledger.iter_events())), harness.schemas


@pytest.fixture
def actors() -> Actors:
    return Actors(owner=OWNER)


def _replay(forger: Forger, schemas: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("pinned_signatures", (PIN,))
    return replay_legacy(forger.events, schemas=schemas, **kwargs)


def _segmented() -> dict[str, Any]:
    return SEGMENTER.segment(TRACKER, "tracker_task_row")


def _full_flow(base_forger: Forger, actors: Actors) -> tuple[Forger, dict[str, dict[str, Any]]]:
    """A registration, a membership table, a tracker registration and inventory, and one observation of each kind."""
    forger, registration = flows.registered(base_forger, actors)
    forger, table = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1)
    forger, tracker = flows.registered(
        forger, actors, start=30, path="tracker.md", role="legacy_coordination", file_id="2"
    )
    forger, inventory = flows.inventory_recorded(forger, actors, tracker, _segmented(), start=40)
    whole = flows.observation(forger.project_id, actors.observer, at(50), registration, PIN)
    forger = forger.row("LR-015", whole["record_id"], whole, actor=actors.observer, when=at(50))
    family_set = flows.observation(
        forger.project_id,
        actors.observer,
        at(51),
        registration,
        PIN,
        count=1,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", PIN)],
    )
    forger = forger.row("LR-015", family_set["record_id"], family_set, actor=actors.observer, when=at(51))
    row = inventory["rows"][0]
    item = flows.observation(
        forger.project_id,
        actors.observer,
        at(52),
        tracker,
        PIN,
        selector={
            "selector_kind": "inventory_item",
            "inventory_ref": flows.record_ref(inventory),
            "row_ordinal": 1,
            "anchor_text": row["anchor_text"],
            "raw_row_sha256": row["raw_row_sha256"],
        },
        families=[flows.signed_family("item", PIN)],
    )
    forger = forger.row("LR-015", item["record_id"], item, actor=actors.observer, when=at(52))
    return forger, {
        "registration": registration,
        "table": table,
        "tracker": tracker,
        "inventory": inventory,
        "whole": whole,
        "family_set": family_set,
        "item": item,
    }


# --- The whole flow (note §17, first row) ----------------------------------------------------------------------------


def test_whole_flow_replays_through_every_public_replay(base, actors, monkeypatch, tmp_path: Path) -> None:
    forger, records = _full_flow(*base[:1], actors)
    schemas = base[1]
    # The public replay calls replay_legacy with the code's pins, so the test pin is injected there.
    monkeypatch.setattr(accepted_w9, "ACCEPTED_W0_SIGNATURES", (PIN,))
    replay_projection(forger.events, schema_registry=schemas)
    rebuild_projection(forger.events, tmp_path / "projection.json", schemas)
    replay_discovery(forger.events, schemas=schemas)
    state = replay_legacy(forger.events, schemas=schemas)
    assert set(state["records"]["legacy_path_registration"]) == {
        records["registration"]["record_id"],
        records["tracker"]["record_id"],
    }
    assert set(state["records"]["legacy_observation"]) == {
        records[key]["record_id"] for key in ("whole", "family_set", "item")
    }
    assert state["row_counts"] == {
        "LR-001": 1,
        **{row: 2 for row in ("LR-003", "LR-004", "LR-005")},
        **{f"LR-{n:03d}": 1 for n in range(6, 15)},
        "LR-015": 3,
    }
    # Every pre-assigned ID was reserved and then used.
    assert all(reservation["used"] for reservation in state["reservations"].values())
    assert state["stale_observations"] == []


# --- N-2 and the pre-assigned refs (§4.1, §4.2) -----------------------------------------------------------------------

DAY = 24 * 60


def _refused(forger: Forger, schemas: Any, message: str, **kwargs: Any) -> None:
    with pytest.raises(IntegrityError, match=message):
        _replay(forger, schemas, **kwargs)


def test_n2_a_record_whose_content_hash_hashes_other_content_is_refused(base, actors) -> None:
    forger, schemas = base
    record = flows.registration(forger.project_id, actors.analyst, at(0))
    record["content_hash"] = record_content_hash({**record, "normalized_path": "results/other.json"})
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(0))
    _refused(forged, schemas, "W9 record content_hash is not the hash of its content")


def test_a_pre_assigned_ref_hash_other_than_the_rule_is_refused(base, actors) -> None:
    forger, schemas = base
    record = flows.registration(forger.project_id, actors.analyst, at(0))
    record["registration_decision_ref"]["content_hash"] = "0" * 64
    flows.stamp(record)
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(0))
    _refused(forged, schemas, "W9 pre-assigned registration_decision_ref hash is not the pre-assigned ref rule")


def test_a_second_proposal_pre_assigning_a_reserved_id_is_refused(base, actors) -> None:
    forger, schemas = base
    first = flows.registration(forger.project_id, actors.analyst, at(0))
    forger = forger.row("LR-003", first["record_id"], first, actor=actors.analyst, when=at(0))
    second = flows.registration(forger.project_id, actors.analyst, at(1), path="results/y.json", file_id="9")
    second["registration_decision_ref"] = pre_assigned_ref(
        "decision", first["registration_decision_ref"]["id"], second["record_id"]
    )
    flows.stamp(second)
    forged = forger.row("LR-003", second["record_id"], second, actor=actors.analyst, when=at(1))
    _refused(forged, schemas, "W9 pre-assigned ID is already claimed or reserved")


def test_a_review_request_using_another_proposals_reservation_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, first = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1, stop_after="LR-006")
    forger, second = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, start=100, stop_after="LR-006"
    )
    request = flows.review_request(
        "LR-007",
        second,
        first["review_ref"]["id"],
        actors.reviewer,
        at(101),
        sessions=("session-analyst", "session-author"),
    )
    forged = forger.row("LR-007", first["review_ref"]["id"], request, actor=actors.analyst, when=at(101))
    _refused(forged, schemas, "W9 review ID is not the proposal's pre-assigned review")


def test_a_claiming_event_not_at_version_1_of_its_own_stream_is_refused(base, actors) -> None:
    forger, schemas = base
    record = flows.registration(forger.project_id, actors.analyst, at(0))
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(0), stream_versions={0: 2})
    _refused(forged, schemas, "W9 proposal is not at its own stream's version 1")
    forged = forger.row("LR-003", new_id("scope_definition"), record, actor=actors.analyst, when=at(0))
    _refused(forged, schemas, "W9 proposal is not at its own stream's version 1")


def test_preparer_set_fields_must_be_the_events(base, actors) -> None:
    forger, schemas = base
    record = flows.registration(forger.project_id, actors.analyst, at(0))
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.observer, when=at(0))
    _refused(forged, schemas, "W9 record created_by_actor_id is not the event's actor")
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(5))
    _refused(forged, schemas, "W9 record created_at is not the event's time")


# --- The W2 payload fields (§5.2): one control per checked field -------------------------------------------------------

REQUEST_FIELD_CONTROLS = [
    ("review_type", "provenance", "W9 review request review_type is not the fixed value"),
    ("governing_refs", ["W9:LR-007", "extra"], "W9 review request governing_refs is not the fixed value"),
    ("required_lanes", ["provenance", "statistics"], "W9 review request required_lanes is not the fixed value"),
    ("required_independence_grade", "same_family", "required_independence_grade is not the fixed value"),
    ("visibility_policy", "public", "W9 review request visibility_policy is not the fixed value"),
    (
        "allowed_verdicts",
        ["approve", "approve_with_conditions", "changes_requested", "reject", "unable_to_verify"],
        "W9 review request allowed_verdicts is not the fixed value",
    ),
    ("satisfaction_authority", "ars://legacy/policy/other@1.0.0", "satisfaction_authority is not the fixed value"),
    ("escalation_rule", "none", "W9 review request escalation_rule is not the fixed value"),
    ("deadline", "2030-01-01T00:00:00Z", "W9 review request deadline is not the fixed value"),
    ("subject_hashes", ["b" * 64], "W9 review request subject hash is not the proposal's current hash"),
    ("subject_hashes", ["b" * 64, "c" * 64], "W9 review request subjects and hashes are not paired"),
    ("review_questions", [], "W9 review request carries no review question"),
    ("reviewer_capability", [], "W9 review request must name exactly one reviewer"),
    ("reviewer_capability", [new_id("actor"), new_id("actor")], "W9 review request must name exactly one reviewer"),
    ("required_evidence_refs", ["w9-analyst-session:a"], "session refs are not the required count"),
    (
        "required_evidence_refs",
        ["w9-analyst-session:", "w9-author-session:b"],
        "W9 review request session ref is malformed or empty",
    ),
    (
        "required_evidence_refs",
        ["w9-author-session:b", "w9-analyst-session:a"],
        "W9 review request session ref is malformed or empty",
    ),
]


@pytest.mark.parametrize(("field", "value", "message"), REQUEST_FIELD_CONTROLS)
def test_review_request_field_controls(base, actors, field: str, value: Any, message: str) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, tweaks={"LR-007": flows.Tweak({field: value})}, stop_after="LR-007"
    )
    _refused(forged, schemas, message)


VERDICT_FIELD_CONTROLS = [
    ("verdict", "approve_with_conditions", "W9 verdict is not an allowed verdict"),
    ("conditions", [{"text": "later"}], "W9 verdict conditions is not the derived value"),
    ("required_evidence_refs", ["w9-analyst-session:x"], "W9 verdict required_evidence_refs is not the derived"),
    ("reviewer_profile", "other", "W9 verdict reviewer_profile is not the derived value"),
    ("context_manifest_id", new_id("context"), "W9 verdict context_manifest_id is not the derived value"),
    ("producing_attempt_id", new_id("attempt"), "W9 verdict producing_attempt_id is not the derived value"),
    ("trace_visibility_evidence_refs", [], "trace_visibility_evidence_refs is not the derived value"),
    ("computed_independence_grade", "same_family", "computed_independence_grade is not the derived value"),
    ("unchanged_subject_sha256", "b" * 64, "W9 verdict subject hash is stale"),
    ("reviewer_session", "session-analyst", "W9 reviewer session is a session the request records"),
    ("reviewer_session", "session-author", "W9 reviewer session is a session the request records"),
    ("reviewer_actor_id", new_id("actor"), "W9 verdict is not recorded by the reviewer the request named"),
]


@pytest.mark.parametrize(("field", "value", "message"), VERDICT_FIELD_CONTROLS)
def test_review_verdict_field_controls(base, actors, field: str, value: Any, message: str) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, tweaks={"LR-008": flows.Tweak({field: value})}, stop_after="LR-008"
    )
    _refused(forged, schemas, message)


def test_w9_c21_a_verdict_by_anyone_but_the_named_reviewer_is_refused(base, actors) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, tweaks={"LR-008": flows.Tweak(actor=actors.analyst)}
    )
    _refused(forged, schemas, "W9 verdict is not recorded by the reviewer the request named")


DECISION_FIELD_CONTROLS = [
    ("decision_revision", 2, "W9 Decision proposal decision_revision is not the fixed value"),
    ("decision_kind", "design_lock", "W9 Decision proposal decision_kind is not the fixed value"),
    ("options", ["accept"], "W9 Decision proposal options is not the fixed value"),
    ("affected_task_ids", [new_id("task")], "W9 Decision proposal affected_task_ids is not the fixed value"),
    ("affected_claim_ids", ["clm"], "W9 Decision proposal affected_claim_ids is not the fixed value"),
    ("required_authority", "delegate", "W9 Decision proposal required_authority is not the fixed value"),
    ("review_date", "2026-09-01T00:00:00Z", "W9 Decision proposal review_date is not the fixed value"),
    ("expires_at", "2030-01-01T00:00:00Z", "W9 Decision proposal expires_at is not the fixed value"),
    ("governing_evidence_refs", ["W9:LR-009"], "W9 Decision proposal does not encode its subject"),
]


@pytest.mark.parametrize(("field", "value", "message"), DECISION_FIELD_CONTROLS)
def test_decision_proposal_field_controls(base, actors, field: str, value: Any, message: str) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, tweaks={"LR-009": flows.Tweak({field: value})}, stop_after="LR-009"
    )
    _refused(forged, schemas, message)


def test_w9_c22_a_decision_proposal_on_another_hash_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, record = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1, stop_after="LR-008")
    refs = ["W9:LR-009", f"w9-subject:{record['record_id']}", f"w9-subject-sha256:{'b' * 64}"]
    proposal = flows.decision_proposal(
        "LR-009", record, record["acceptance_decision_ref"]["id"], at(13), governing_evidence_refs=refs
    )
    forged = forger.row("LR-009", proposal["new_decision_id"], proposal, actor=actors.analyst, when=at(13))
    _refused(forged, schemas, "W9 Decision proposal subject hash is not the proposal's current hash")


RESOLUTION_FIELD_CONTROLS = [
    ("selected_option", "reject", "W9 Decision resolution selected_option is not the required value"),
    ("effective_scope", "w9-record:other", "W9 Decision resolution effective_scope is not the required value"),
    ("decision_revision", 2, "W9 Decision resolution decision_revision is not the required value"),
    ("deciding_actor_id", new_id("actor"), "W9 Decision resolution deciding_actor_id is not the required value"),
    ("decision_authority_grant_id", new_id("authority_grant"), "decision_authority_grant_id is not the required"),
    (
        "governing_evidence_refs",
        ["W9:LR-010", "w9-subject:other", "w9-subject-sha256:other"],
        "W9 Decision resolution governing_evidence_refs is not the required value",
    ),
    ("considered_review_ids", [], "W9 Decision resolution considered_review_ids is not the required value"),
    ("effective_at", "2026-09-01T00:00:00Z", "W9 Decision resolution effective_at is not the required value"),
    ("permitted_commands", ["X"], "W9 Decision resolution permitted_commands is not the required value"),
    ("superseded_decision_ids", [new_id("decision")], "superseded_decision_ids is not the required value"),
    ("conditions", [{"text": "later"}], "W9 Decision resolution conditions is not the required value"),
    ("revisit_triggers", ["x"], "W9 Decision resolution revisit_triggers is not the required value"),
]


@pytest.mark.parametrize(("field", "value", "message"), RESOLUTION_FIELD_CONTROLS)
def test_decision_resolution_field_controls(base, actors, field: str, value: Any, message: str) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, tweaks={"LR-010": flows.Tweak({field: value})}
    )
    _refused(forged, schemas, message)


def test_a_resolution_after_expires_at_is_refused(base, actors) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, tweaks={"LR-010": flows.Tweak(minutes=3 + 30 * DAY + 1)}
    )
    _refused(forged, schemas, "W9 Decision resolved after it expired")


# --- Review satisfaction and roles (§5.4, §5.5; W9-C20) -------------------------------------------------------------


def test_b_a_decision_proposal_needs_an_approved_review(base, actors) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger,
        actors,
        sha256=SOURCE_SHA,
        size=1,
        tweaks={"LR-008": flows.Tweak({"verdict": "changes_requested"})},
        stop_after="LR-009",
    )
    _refused(forged, schemas, "W9 Decision proposal has no satisfied review on the current hash")


@pytest.mark.parametrize("who", ["author", "analyst"])
def test_w9_c20_a_reviewer_who_is_the_author_or_the_analyst_is_refused(base, actors, who: str) -> None:
    forger, schemas = base
    named = getattr(actors, who)
    forged, _ = flows.membership_recorded(
        forger,
        actors,
        sha256=SOURCE_SHA,
        size=1,
        tweaks={"LR-007": flows.Tweak({"reviewer_capability": [named]})},
        stop_after="LR-007",
    )
    _refused(forged, schemas, "W9 reviewer is the proposal's creator, author or the requesting analyst")


def test_w9_c20_an_analyst_who_is_the_author_is_refused(base, actors) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger,
        actors,
        sha256=SOURCE_SHA,
        size=1,
        tweaks={"LR-007": flows.Tweak(actor=actors.author)},
        stop_after="LR-007",
    )
    _refused(forged, schemas, "W9 analyst is the proposal's creator")


def test_w9_c20_a_reviewer_on_the_authors_session_is_refused_though_the_actors_differ(base, actors) -> None:
    """The template's author-session limb (§5.5): distinct actors on one session."""
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger,
        actors,
        sha256=SOURCE_SHA,
        size=1,
        tweaks={"LR-008": flows.Tweak({"reviewer_session": "session-author"})},
        stop_after="LR-008",
    )
    assert actors.reviewer != actors.author
    _refused(forged, schemas, "W9 reviewer session is a session the request records")


def test_a_reproducer_who_is_the_observer_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, tracker = flows.registered(forger, actors, path="tracker.md", role="legacy_coordination")
    record = flows.inventory(forger.project_id, actors.observer, at(20), tracker, _segmented())
    forger = forger.row("LR-011", record["record_id"], record, actor=actors.observer, when=at(20))
    review_id = record["independent_reproduction_ref"]["id"]
    request = flows.review_request("LR-012", record, review_id, actors.observer, at(21))
    forged = forger.row("LR-012", review_id, request, actor=actors.analyst, when=at(21))
    _refused(forged, schemas, "W9 reviewer is the proposal's creator, author or the requesting analyst")


# --- Lapse (§4.6) -----------------------------------------------------------------------------------------------------


def test_a_corrected_registration_is_refused_while_the_first_is_open_and_admitted_once_it_lapsed(base, actors) -> None:
    forger, schemas = base
    first = flows.registration(forger.project_id, actors.analyst, at(0))
    forger = forger.row("LR-003", first["record_id"], first, actor=actors.analyst, when=at(0))
    for minutes, admitted in ((29 * DAY, False), (30 * DAY, True)):
        corrected = flows.registration(forger.project_id, actors.analyst, at(minutes), file_id="7")
        forged = forger.row("LR-003", corrected["record_id"], corrected, actor=actors.analyst, when=at(minutes))
        if admitted:
            _replay(forged, schemas)
        else:
            _refused(forged, schemas, "W9 registration of a path or physical identity already registered or proposed")


def test_the_lapse_time_is_the_later_of_the_term_and_the_decisions_expiry(base, actors) -> None:
    forger, schemas = base
    first = flows.registration(forger.project_id, actors.analyst, at(0))
    forger = forger.row("LR-003", first["record_id"], first, actor=actors.analyst, when=at(0))
    decision_id = first["registration_decision_ref"]["id"]
    proposal = flows.decision_proposal("LR-004", first, decision_id, at(20 * DAY))
    forger = forger.row("LR-004", decision_id, proposal, actor=actors.analyst, when=at(20 * DAY))
    for minutes, admitted in ((35 * DAY, False), (50 * DAY, True)):
        corrected = flows.registration(forger.project_id, actors.analyst, at(minutes), file_id="7")
        forged = forger.row("LR-003", corrected["record_id"], corrected, actor=actors.analyst, when=at(minutes))
        if admitted:
            _replay(forged, schemas)
        else:
            _refused(forged, schemas, "already registered or proposed")


@pytest.mark.parametrize("row", ["LR-007", "LR-009"])
def test_a_lapsed_proposal_cannot_be_reviewed_or_decided(base, actors, row: str) -> None:
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger,
        actors,
        sha256=SOURCE_SHA,
        size=1,
        tweaks={row: flows.Tweak(minutes=31 * DAY)},
        stop_after=row,
    )
    _refused(forged, schemas, "W9 step names a lapsed proposal")


def test_a_lapsed_proposal_cannot_be_resolved(base, actors) -> None:
    """Resolved exactly at the Decision's expiry: not after it, so only the lapse refuses.

    Review i-1 (WP9.3-1b record §4): at the instant ``expires_at == lapse_at``, §5.2's "not after ``expires_at``" admits
    and §4.6's "open while before the lapse" refuses. The stricter test governs, and this test pins that instant.
    """
    forger, schemas = base
    forged, _ = flows.membership_recorded(
        forger, actors, sha256=SOURCE_SHA, size=1, tweaks={"LR-010": flows.Tweak(minutes=3 + 30 * DAY)}
    )
    _refused(forged, schemas, "W9 step names a lapsed proposal")


# --- G5 and F-8 (§6.1) ------------------------------------------------------------------------------------------------


def test_f8_a_resolution_whose_decision_names_another_record_is_refused(base, actors) -> None:
    forger, schemas = base
    first = flows.registration(forger.project_id, actors.analyst, at(0))
    second = flows.registration(forger.project_id, actors.analyst, at(0), path="results/y.json", file_id="9")
    for record in (first, second):
        forger = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(0))
    decision_id = first["registration_decision_ref"]["id"]
    proposal = flows.decision_proposal("LR-004", first, decision_id, at(1))
    forger = forger.row("LR-004", decision_id, proposal, actor=actors.analyst, when=at(1))
    grant = new_id("authority_grant")
    resolved = flows.resolution("LR-005", proposal, first, OWNER, grant, at(2), [])
    forged = forger.append(
        "ResolveW9AuthorityDecision",
        [("DecisionResolved", decision_id, resolved), ("LegacyPathRegistrationRecorded", second["record_id"], second)],
        actor=OWNER,
        when=at(2),
        grant=grant,
    )
    _refused(forged, schemas, "W9 resolved record is not its Decision's subject")


# --- Cross-partition identity (§4.3) ---------------------------------------------------------------------------------


@pytest.mark.parametrize("order", ["before", "after"])
def test_a_w9_proposal_on_an_id_a_non_w9_event_takes_is_refused(base, actors, order: str) -> None:
    forger, schemas = base
    record = flows.registration(forger.project_id, actors.analyst, at(0))
    foreign = ("RegisterCandidate", "CandidateRegistered", record["record_id"], {"candidate_id": record["record_id"]})
    if order == "before":
        forger = forger.foreign(*foreign)
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(0))
    if order == "after":
        forged = forged.foreign(*foreign)
    _refused(forged, schemas, "W9 identity is taken by a non-W9 event")


def test_a_non_w9_event_creating_a_w9_reserved_review_id_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, record = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1, stop_after="LR-006")
    review_id = record["review_ref"]["id"]
    forged = forger.foreign(
        "RecordScientificReview", "ScientificReviewRecorded", new_id("artefact"), {"review_id": review_id}
    )
    _refused(forged, schemas, "W9 identity is taken by a non-W9 event")


def test_a_non_w9_event_referring_to_a_w9_record_is_admitted(base, actors) -> None:
    """A reference is not a creation (§4.3): a listed reference field, and a field the table does not list."""
    forger, schemas = base
    forger, record = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1)
    forger = forger.foreign(
        "WithdrawReview", "ReviewWithdrawn", new_id("review"), {"review_id": record["review_ref"]["id"]}
    )
    forger = forger.foreign("RecordNote", "NoteRecorded", new_id("scope_definition"), {"note_ref": record["record_id"]})
    _replay(forger, schemas)


def test_a_non_w9_event_on_a_w9_fixed_identity_is_refused(base) -> None:
    forger, schemas = base
    for identity in (CATALOGUE_STREAM_ID, sorted(RESERVED_IDS)[0], PIN["ref"]["id"]):
        forged = forger.foreign("CreateScopeDefinition", "ScopeDefinitionCreated", identity, {})
        _refused(forged, schemas, "a non-W9 event takes a W9 fixed identity")


# --- The observation ID and staleness (§5.3, §7.2) --------------------------------------------------------------------


def _observed(forger: Forger, actors: Actors, registration: dict, minutes: float, **kwargs: Any):
    record = flows.observation(forger.project_id, actors.observer, at(minutes), registration, PIN, **kwargs)
    return forger.row("LR-015", record["record_id"], record, actor=actors.observer, when=at(minutes)), record


def test_an_observation_whose_record_id_is_not_derived_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    record = flows.observation(forger.project_id, actors.observer, at(5), registration, PIN)
    record["record_id"] = new_id("scope_definition")
    flows.stamp(record)
    forged = forger.row("LR-015", record["record_id"], record, actor=actors.observer, when=at(5))
    _refused(forged, schemas, "W9 observation record_id is not derived from its subject")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("observed_at", "2026-01-01T00:00:00.000000Z", "W9 observation observed_at is not the event's time"),
        (
            "non_inferences",
            ["an observer's own words"],
            "W9 observation non_inferences are not the fixed strings for its source kind",
        ),
        (
            "non_inferences",
            ["no authority from file presence (W0 §4)", "no Git identity"],
            "W9 observation non_inferences are not the fixed strings for its source kind",
        ),
        (
            "non_inferences",
            ["no Git identity", "no authority from file presence (W0 §4)"],
            "W9 observation non_inferences are not the fixed strings for its source kind",
        ),
    ],
    ids=["observed-at", "other-words", "another-kinds", "reordered"],
)
def test_an_observations_preparer_set_time_and_fixed_non_inferences_are_checked(
    base, actors, field: str, value: Any, message: str
) -> None:
    """Review i-2: ``observed_at`` is the event's time (§5.1) and ``non_inferences`` are §7.4's strings for the kind."""
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    record = flows.observation(forger.project_id, actors.observer, at(5), registration, PIN)
    record[field] = value
    flows.stamp(record)
    forged = forger.row("LR-015", record["record_id"], record, actor=actors.observer, when=at(5))
    _refused(forged, schemas, message)


def test_an_observation_with_the_wrong_count_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    forger, _ = _observed(forger, actors, registration, 5)
    forged, _ = _observed(forger, actors, registration, 6, count=0, source=flows.tracked(sha256="b" * 64))
    _refused(forged, schemas, "W9 observation record_id is not derived from its subject")


def test_a_source_observed_a_then_b_then_a_gets_a_fresh_id_and_is_not_stale(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    ids = []
    for count, sha in enumerate(("a" * 64, "b" * 64, "a" * 64)):
        source = flows.tracked(sha256=sha, blob=("1" if sha[0] == "a" else "3") * 40)
        forger, record = _observed(forger, actors, registration, 5 + count, count=count, source=source)
        ids.append(record["record_id"])
    state = _replay(forger, schemas)
    assert len(set(ids)) == 3
    assert state["stale_observations"] == ids[:2]


# --- W0 signature pins (§9.1) ----------------------------------------------------------------------------------------


def test_with_no_pinned_signature_every_observation_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    forged, _ = _observed(forger, actors, registration, 5)
    _refused(forged, schemas, "no accepted W0-D1 signature", pinned_signatures=())


def test_a_family_whose_signature_is_not_pinned_is_refused(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    other = flows.signature()
    forged, _ = _observed(forger, actors, registration, 5, families=[flows.signed_family("whole_file", other)])
    _refused(forged, schemas, "W9 family's signature ref is not a pinned W0 signature")
    family = flows.signed_family("whole_file", PIN)
    family["signed_w0_revision_ref"]["git_blob"] = "4" * 40
    forged, _ = _observed(forger, actors, registration, 5, families=[family])
    _refused(forged, schemas, "W9 family's signed W0 revision is not a document its signature signs")


def test_a_proposal_pre_assigning_a_pinned_id_is_refused_and_a_ledger_claiming_it_fails_under_the_new_pin(
    base, actors
) -> None:
    forger, schemas = base
    record = flows.registration(forger.project_id, actors.analyst, at(0))
    claimed = record["registration_decision_ref"]["id"]
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(0))
    # Before the pin, the ledger replays; under a pin set that adds the claimed ID it fails (the cross-pin control).
    _replay(forged, schemas, pinned_signatures=(PIN,))
    later = {**PIN, "ref": {**PIN["ref"], "id": claimed}}
    _refused(forged, schemas, "W9 identity is a pinned W0 signature ref", pinned_signatures=(PIN, later))
    # A re-derived #2 ref is another ID, which the ledger does not claim, so it is accepted.
    from research_system.legacy.records import w0_signature_ref_id

    rederived = {**PIN, "ref": {**PIN["ref"], "id": w0_signature_ref_id(PIN["domain"], PIN["accepted_at"], 2)}}
    _replay(forged, schemas, pinned_signatures=(PIN, rederived))


# --- Selectors, families, qualifiers and precedence (§8, §9; W9-T1, T3, T4, T13, T22) ---------------------------------


def test_w9_t3_membership_families_are_exclusive(base, actors) -> None:
    forger, schemas = base
    cases = [
        (
            [
                {"name": "a", "definition_source": "x", "pointers": ["/a"]},
                {"name": "a", "definition_source": "x", "pointers": ["/b"]},
            ],
            [],
            "W9 membership family names are not unique",
        ),
        (
            [
                {"name": "a", "definition_source": "x", "pointers": ["/a"]},
                {"name": "b", "definition_source": "x", "pointers": ["/a"]},
            ],
            [],
            "W9 membership pointer or pattern is in two families",
        ),
        (
            [{"name": "a", "definition_source": "x", "pointers": ["/a"]}],
            ["/a"],
            "unassigned pointer is also in a family",
        ),
    ]
    for families, unassigned, message in cases:
        record = flows.membership(
            forger.project_id, actors.author, at(0), sha256=SOURCE_SHA, size=1, families=families, unassigned=unassigned
        )
        forged = forger.row("LR-006", record["record_id"], record, actor=actors.author, when=at(0))
        _refused(forged, schemas, message)
    record = flows.membership(
        forger.project_id, actors.analyst, at(0), sha256=SOURCE_SHA, size=1, author_actor_id=actors.author
    )
    forged = forger.row("LR-006", record["record_id"], record, actor=actors.analyst, when=at(0))
    _refused(forged, schemas, "W9 membership table is not proposed by its author")


def test_w9_t3_a_table_with_unassigned_pointers_refuses_the_observation(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    forger, table = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1, unassigned=["/loose"])
    selector = {
        "selector_kind": "json_family_set",
        "membership_ref": flows.record_ref(table),
        "family_names": ["headline"],
    }
    forged, _ = _observed(
        forger, actors, registration, 30, selector=selector, families=[flows.signed_family("headline", PIN)]
    )
    _refused(forged, schemas, "W9 membership table has unassigned pointers")


@pytest.mark.parametrize(
    ("names", "source_sha", "importer_is_author", "message"),
    [
        (["missing"], SOURCE_SHA, False, "W9 observation family is not a family of its membership table"),
        (["headline"], "b" * 64, False, "W9 observed bytes are not bytes its membership table applies to"),
        (["headline"], SOURCE_SHA, True, "W9 membership table author is the observation's observer or importer"),
    ],
)
def test_json_family_set_observation_controls(
    base, actors, names: list[str], source_sha: str, importer_is_author: bool, message: str
) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    forger, table = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1)
    selector = {"selector_kind": "json_family_set", "membership_ref": flows.record_ref(table), "family_names": names}
    forged, _ = _observed(
        forger,
        actors,
        registration,
        30,
        selector=selector,
        families=[flows.signed_family(name, PIN) for name in names],
        source=flows.tracked(sha256=source_sha),
        importer=actors.author if importer_is_author else None,
    )
    _refused(forged, schemas, message)


def test_a_whole_file_observation_carries_exactly_one_whole_file_family(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    families = [flows.signed_family("whole_file", PIN), flows.signed_family("extra", PIN)]
    forged, _ = _observed(forger, actors, registration, 5, families=families)
    _refused(forged, schemas, "W9 whole_file observation must carry exactly one family named whole_file")


def test_w9_t22_a_duplicate_anchor_row_is_never_observable(base, actors) -> None:
    """Two rows for one task ID are both duplicate_anchor blockers, and an observation of either is refused."""
    forger, schemas = base
    forger, tracker = flows.registered(forger, actors, path="tracker.md", role="legacy_coordination")
    duplicate = SEGMENTER.segment(
        b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n| 1.1 | b |\n", "tracker_task_row"
    )
    assert [row["blocker_reason"] for row in duplicate["rows"]] == ["duplicate_anchor", "duplicate_anchor"]
    forger, inventory = flows.inventory_recorded(forger, actors, tracker, duplicate, start=20)
    for ordinal, row in enumerate(inventory["rows"], start=1):
        selector = {
            "selector_kind": "inventory_item",
            "inventory_ref": flows.record_ref(inventory),
            "row_ordinal": ordinal,
            "anchor_text": row["anchor_text"],
            "raw_row_sha256": row["raw_row_sha256"],
        }
        forged, _ = _observed(
            forger, actors, tracker, 30, selector=selector, families=[flows.signed_family("item", PIN)]
        )
        _refused(forged, schemas, "W9 inventory item selector names no observable item row")


def test_w9_t1_a_done_status_word_yields_no_acceptance_and_the_payloads_class(base, actors) -> None:
    forger, schemas = base
    forger, tracker = flows.registered(forger, actors, path="tracker.md", role="legacy_coordination")
    segmented = SEGMENTER.segment(
        b"## Task Tracking\n| Task | Status |\n|---|---|\n| 1.1 | Done |\n", "tracker_task_row"
    )
    forger, inventory = flows.inventory_recorded(forger, actors, tracker, segmented, start=20)
    row = inventory["rows"][0]
    selector = {
        "selector_kind": "inventory_item",
        "inventory_ref": flows.record_ref(inventory),
        "row_ordinal": 1,
        "anchor_text": row["anchor_text"],
        "raw_row_sha256": row["raw_row_sha256"],
    }
    forger, record = _observed(
        forger, actors, tracker, 30, selector=selector, families=[flows.signed_family("item", PIN, "unverified")]
    )
    state = _replay(forger, schemas)
    assert state["records"]["legacy_observation"][record["record_id"]]["families"][0]["w0_class"] == "unverified"
    assert not {"legacy_closed_reference_acceptance", "legacy_adoption_decision"} & set(state["records"])
    assert not any(
        event["command_type"] not in {"ImportAcceptedW11CatalogueGenesis"} and "Accept" in event["event_type"]
        for event in forger.events
    )


def test_w9_t13_corrected_by_must_name_a_tier_one_source_and_line_spans_are_ordered(base, actors) -> None:
    forger, schemas = base
    forger, result = flows.registered(forger, actors)
    forger, log = flows.registered(forger, actors, start=5, path="log.md", role="legacy_coordination", file_id="2")

    def qualifier(path: str, first: int = 1, last: int = 2) -> dict[str, Any]:
        locator = {
            **flows.tracked(path),
            "locator_kind": "git_file",
            "line_span": {"first_line": first, "last_line": last},
        }
        locator.pop("identity_kind")
        return {"qualifier_kind": "corrected_by", "source_ref": locator, "text": "corrected"}

    forged, _ = _observed(forger, actors, log, 10, qualifiers=[qualifier("log.md")])
    _refused(forged, schemas, "W9 corrected_by source is not a precedence tier 1 source")
    forged, _ = _observed(forger, actors, log, 10, qualifiers=[qualifier("results/x.json", 5, 2)])
    _refused(forged, schemas, "W9 locator line span is inverted")
    admitted, _ = _observed(forger, actors, log, 10, qualifiers=[qualifier("results/x.json")])
    _replay(admitted, schemas)


def test_w9_t4_a_stale_projection_family_needs_a_conflict_naming_the_observed_record(base, actors) -> None:
    forger, schemas = base
    forger, registration = flows.registered(forger, actors)
    family = [flows.signed_family("whole_file", PIN, "stale_projection")]
    forged, _ = _observed(forger, actors, registration, 5, families=family)
    _refused(forged, schemas, "W9 stale_projection family has no conflict naming the observed record")
    own = {**flows.tracked(), "locator_kind": "git_file", "line_span": None}
    own.pop("identity_kind")
    other = {**own, "repository_path": "results/stronger.json"}
    conflict = {"conflicting_record_refs": [own, other], "resolution": "resolved_by_precedence", "precedence_tier": 1}
    admitted, _ = _observed(forger, actors, registration, 5, families=family, conflicts=[conflict])
    _replay(admitted, schemas)


# --- Registration and inventory rows (§6.2) ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "path": ".research-system/projections/legacy/x.json",
                "role": "legacy_research_result",
                "kind": "untracked_file",
            },
            "W9 legacy role under the legacy projection directory",
        ),
        (
            {
                "path": "notes/conv.md",
                "root_kind": "vault_root",
                "kind": "vault_file",
                "target": "C:/TDL/CONVENTIONS.md",
            },
            "W9 registration resolves to CONVENTIONS.md outside the conventions lock",
        ),
    ],
    ids=["projection-directory", "conventions-vault-alias"],
)
def test_registration_row_controls(base, actors, kwargs: dict[str, Any], message: str) -> None:
    forger, schemas = base
    record = flows.registration(forger.project_id, actors.analyst, at(0), **kwargs)
    forged = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(0))
    _refused(forged, schemas, message)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda record: record["rows"][0].update(row_ordinal=2), "W9 inventory row ordinals do not run 1 to n"),
        (
            lambda record: record["rows"][0].update(selector_kind="heading_section"),
            "W9 event payload does not validate against its record schema",
        ),
        (
            lambda record: record.update(read_ended_at="2026-08-31T00:00:00.000000Z"),
            "W9 inventory read ends before it starts",
        ),
        (
            lambda record: record.update(source_identity=flows.tracked("other.md")),
            "W9 source does not match its registration's kind, root and path",
        ),
    ],
    ids=["ordinals", "selector-kind", "read-order", "source-path"],
)
def test_inventory_row_controls(base, actors, mutate: Any, message: str) -> None:
    forger, schemas = base
    forger, tracker = flows.registered(forger, actors, path="tracker.md", role="legacy_coordination")
    record = flows.inventory(forger.project_id, actors.observer, at(20), tracker, _segmented())
    mutate(record)
    flows.stamp(record)
    forged = forger.row("LR-011", record["record_id"], record, actor=actors.observer, when=at(20))
    _refused(forged, schemas, message)


def test_a_computational_log_registration_is_refused_without_an_accepted_export(base, actors) -> None:
    forger, schemas = base
    forger, log = flows.registered(
        forger,
        actors,
        path="04-Methods/Computational-Log.md",
        role="legacy_decision_log_entry",
        root_kind="vault_root",
        kind="vault_file",
    )
    record = flows.inventory(
        forger.project_id, actors.observer, at(20), log, _segmented(), source=flows.tracked("export/cl.md")
    )
    forged = forger.row("LR-011", record["record_id"], record, actor=actors.observer, when=at(20))
    _refused(forged, schemas, "W9 Computational-Log source needs an accepted export")
