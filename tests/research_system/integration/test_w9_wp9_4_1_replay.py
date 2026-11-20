# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §5 to §9, §15)
# Purpose: forged-ledger replay controls for WP9.4-1 (LR-023 to LR-034, G5/M-2, analyst rule M-3, fixtures L, W9-T9, W9-C20..C25).
"""WP9.4-1 replay controls on forged scratch ledgers (WP9.4 note §5 to §8, §15)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import research_system.legacy.accepted_w9 as accepted_w9
from research_system.discovery.runtime import replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy import projection_read
from research_system.legacy.records import (
    adoption_eligibility_decision_id,
    adoption_review_id,
    pre_assigned_ref,
)
from research_system.legacy.replay import reducers
from research_system.legacy.replay.driver import replay_legacy
from research_system.legacy.routes import LEGACY_ROUTED_ROWS
from research_system.projection.replay import rebuild_projection
from research_system.projection.replay import replay as replay_projection
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_wp9_3_replay import PIN, _full_flow
from tests.research_system.integration.test_w9_wp9_3_replay import base as base  # noqa: F401
from tests.research_system.integration.w9_flows import Actors, Forger, Tweak, at

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture
def actors() -> Actors:
    from tests.research_system.factories import ACTORS

    return Actors(owner=ACTORS["actor-a"])


def _replay(forger: Forger, schemas: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("pinned_signatures", (PIN,))
    return replay_legacy(forger.events, schemas=schemas, **kwargs)


def _refused(forger: Forger, schemas: Any, message: str, **kwargs: Any) -> None:
    with pytest.raises(IntegrityError, match=message):
        _replay(forger, schemas, **kwargs)


@pytest.fixture
def accepted_flow(base, actors) -> tuple[Forger, dict[str, dict[str, Any]], Any]:  # noqa: F811
    """Base flow plus binary and .json whole-file registrations/observations in one accepted batch."""
    forger, records = _full_flow(base[0], actors)
    schemas = base[1]
    forger, bin_reg = flows.registered(
        forger, actors, start=55, path="data/embed.bin", role="legacy_research_result", file_id="3"
    )
    bin_obs = flows.observation(
        forger.project_id,
        actors.observer,
        at(56),
        bin_reg,
        PIN,
        source=flows.tracked("data/embed.bin", sha256="b" * 64, blob="b" * 40),
    )
    forger = forger.row("LR-015", bin_obs["record_id"], bin_obs, actor=actors.observer, when=at(56))
    forger, json_reg = flows.registered(
        forger, actors, start=57, path="results/whole.json", role="legacy_research_result", file_id="4"
    )
    json_whole_obs = flows.observation(
        forger.project_id,
        actors.observer,
        at(58),
        json_reg,
        PIN,
        source=flows.tracked("results/whole.json", sha256="d" * 64, blob="d" * 40),
    )
    forger = forger.row("LR-015", json_whole_obs["record_id"], json_whole_obs, actor=actors.observer, when=at(58))
    batch = flows.acceptance(
        forger.project_id,
        actors.analyst,
        at(60),
        [records["family_set"], records["item"], bin_obs, json_whole_obs],
    )
    transitions = [
        flows.ownership_transition(batch, bin_reg),
        flows.ownership_transition(batch, json_reg),
    ]
    forger = flows.acceptance_recorded(forger, actors, batch, transitions, start=60)
    records = {
        **records,
        "bin_reg": bin_reg,
        "bin_obs": bin_obs,
        "json_reg": json_reg,
        "json_whole_obs": json_whole_obs,
        "acceptance": batch,
    }
    return forger, records, schemas


def _open_finding(obs: dict[str, Any]) -> dict[str, Any]:
    return {
        "qualifier_kind": "open_review_finding",
        "source_ref": flows.record_ref(obs),
        "text": "Rung 4 calibration still pending",
    }


def _accepted_task_obs_with_finding(
    base_forger: Forger, actors: Actors, *, start: float = 0
) -> tuple[Forger, dict[str, Any]]:
    """Create an accepted family observation carrying one ``open_review_finding`` qualifier."""
    forger, reg = flows.registered(
        base_forger, actors, start=start, path="results/stat.json", role="legacy_research_result", file_id="10"
    )
    forger, table = flows.membership_recorded(
        forger, actors, sha256="c" * 64, size=1, start=start + 10, path="results/stat.json"
    )
    finding_source = {
        "locator_kind": "git_file",
        "repository_path": "reviews/r1.md",
        "git_commit": flows.SHA1,
        "git_blob": flows.SHA1,
        "sha256": "f" * 64,
        "byte_length": 10,
        "line_span": None,
    }
    obs = flows.observation(
        forger.project_id,
        actors.observer,
        at(start + 20),
        reg,
        PIN,
        source=flows.tracked("results/stat.json", sha256="c" * 64),
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", PIN)],
        qualifiers=[
            {"qualifier_kind": "open_review_finding", "source_ref": finding_source, "text": "Open calibration finding"}
        ],
    )
    forger = forger.row("LR-015", obs["record_id"], obs, actor=actors.observer, when=at(start + 20))
    batch = flows.acceptance(forger.project_id, actors.analyst, at(start + 30), [obs])
    forger = flows.acceptance_recorded(forger, actors, batch, [], start=start + 30)
    return forger, obs


# --- Positive flows through all 4 public replays (§15) ---------------------------------------------------------------


def test_adoption_and_discharge_positive_flows_replay_through_all_four_boundaries(
    accepted_flow, actors, monkeypatch, tmp_path: Path
) -> None:
    """WP9.4-1 positive adoption (family + whole-file + task-input) and discharge through every public replay."""
    forger, records, schemas = accepted_flow
    monkeypatch.setattr(accepted_w9, "ACCEPTED_W0_SIGNATURES", (PIN,))

    adp_fam = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(70),
        records["family_set"],
        intended_use={"description": "w9-use:manuscript-claims/P01-A", "successor_ref": None},
    )
    forger = flows.adoption_recorded(
        forger,
        actors,
        adp_fam,
        start=70,
        applicable_fixtures=("F-019", "S-017"),
        fixture_refs=[f"w9-fixture:F-019:{new_id('review')}", f"w9-fixture:S-017:{new_id('decision')}"],
    )

    adp_bin = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(80),
        records["bin_obs"],
        subject={"subject_kind": "whole_file", "rehash_at_use": True},
        intended_use={
            "description": "w9-use:task-input/t1.41-embed",
            "successor_ref": {"id": new_id("task"), "record_revision": 1, "content_hash": "d" * 64},
        },
    )
    forger = flows.adoption_recorded(forger, actors, adp_bin, start=80, applicable_fixtures=("F-038", "S-017"))

    dis = flows.discharge(forger.project_id, actors.analyst, at(90))
    forger = flows.discharge_recorded(forger, actors, dis, start=90)

    replay_projection(forger.events, schema_registry=schemas)
    rebuild_projection(forger.events, tmp_path / "projection.json", schemas)
    replay_discovery(forger.events, schemas=schemas)
    state = replay_legacy(forger.events, schemas=schemas)

    assert set(state["records"][reducers.ADOPTION]) == {adp_fam["record_id"], adp_bin["record_id"]}
    assert state["records"][reducers.DISCHARGE] == {dis["record_id"]: dis}
    assert state["row_counts"]["LR-023"] == 2
    assert state["row_counts"]["LR-029"] == 2
    assert state["row_counts"]["LR-030"] == 1
    assert state["row_counts"]["LR-034"] == 1
    assert projection_read.adoption_status(state, adp_fam["record_id"])["status"] == "active"
    assert projection_read.adoption_status(state, adp_bin["record_id"])["status"] == "active"
    assert projection_read.family_admissible(
        state, records["family_set"]["record_id"], "headline", "w9-use:manuscript-claims/P01-A"
    )["admissible"]
    assert projection_read.family_admissible(
        state, records["bin_obs"]["record_id"], "whole_file", "w9-use:task-input/t1.41-embed"
    )["admissible"]


# --- G5 and review_id_for (§5.2, owner point C, M-2, §15) -------------------------------------------------------------


def test_review_id_for_dispatches_explicitly_and_refuses_unlisted_kinds() -> None:
    reg_id = new_id("scope_definition")
    adp_id = new_id("scope_definition")
    when = at(70)
    assert reducers.review_id_for("legacy_path_registration", {"record_id": reg_id}) is reducers.NO_REVIEW_REQUIRED
    assert reducers.review_id_for(reducers.ADOPTION, {"record_id": adp_id, "created_at": when}) == adoption_review_id(
        adp_id, when
    )
    assert reducers.review_id_for(reducers.DISCHARGE, {"reviewer_ref": {"id": "rev_1"}}) == "rev_1"
    for unlisted in ("legacy_paper_root", "legacy_source_inventory", "unknown_kind"):
        with pytest.raises(IntegrityError, match="W9 record kind has no review resolver entry"):
            reducers.review_id_for(unlisted, {"record_id": reg_id, "created_at": when})


def test_g5_for_adoption_refuses_missing_unsatisfied_or_wrong_review_at_lr028_and_lr029(accepted_flow, actors) -> None:
    forger, records, schemas = accepted_flow
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])

    # No review at all at LR-028.
    no_review = flows.adoption_recorded(forger, actors, adp, stop_after="LR-025")
    prop = flows.decision_proposal("LR-028", adp, adp["decision_ref"]["id"], at(75))
    prop["governing_evidence_refs"].extend(
        [f"w9-fixture:F-019:{new_id('review')}", f"w9-fixture:S-017:{new_id('review')}"]
    )
    no_review = no_review.row("LR-028", adp["decision_ref"]["id"], prop, actor=actors.analyst, when=at(75))
    _refused(no_review, schemas, "W9 Decision proposal has no satisfied review on the current hash")

    # Reject verdict fails at LR-028.
    rejected_verdict = flows.adoption_recorded(
        forger, actors, adp, tweaks={"LR-027": Tweak(payload={"verdict": "reject"})}, stop_after="LR-028"
    )
    _refused(rejected_verdict, schemas, "W9 Decision proposal has no satisfied review on the current hash")

    # Non-derived review ID refused at LR-026.
    wrong_rev = flows.adoption_recorded(
        forger, actors, adp, tweaks={"LR-026": Tweak(payload={"new_review_id": new_id("review")})}, stop_after="LR-026"
    )
    _refused(wrong_rev, schemas, "W9 review ID is not the proposal's pre-assigned review")

    # Wrong considered_review_ids at LR-029 refused.
    bad_considered = flows.adoption_recorded(
        forger, actors, adp, tweaks={"LR-029": Tweak(payload={"considered_review_ids": []})}
    )
    _refused(bad_considered, schemas, "W9 Decision resolution considered_review_ids is not the required value")

    # Mutated record at LR-029 (W9-C23) refused.
    tampered = flows.adoption_recorded(forger, actors, adp, stop_after="LR-028")
    decision_prop = tampered.events[-1]["payload"]
    review_id = adoption_review_id(adp["record_id"], adp["created_at"])
    grant = new_id("authority_grant")
    resolved = flows.resolution("LR-029", decision_prop, adp, actors.owner, grant, at(76), [review_id])
    bad_record = flows.stamp({**adp, "w5_consequence": "other"})
    tampered_res = tampered.append(
        "ResolveW9AuthorityDecision",
        [
            ("DecisionResolved", adp["decision_ref"]["id"], resolved),
            ("LegacyAdoptionDecisionRecorded", adp["record_id"], bad_record),
        ],
        actor=actors.owner,
        when=at(76),
        grant=grant,
    )
    _refused(tampered_res, schemas, "W9 resolved record is not its Decision's subject")


def test_lr029_refuses_unsatisfied_or_missing_review_with_valid_lr028_prefix(accepted_flow, actors) -> None:
    """Fix 4 (CodeRabbit #439): exercise LR-029's own review_satisfied guard on a valid LR-028 prefix."""
    forger, records, schemas = accepted_flow
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])
    full = flows.adoption_recorded(forger, actors, adp, start=70)
    review_id = adoption_review_id(adp["record_id"], adp["created_at"])

    state_at_lr028 = _replay(Forger(full.events[:-2]), schemas)
    lr029_tx = full.events[-2:]

    # Negative control: exact unmodified LR-028 state + valid LR-029 transaction resolves cleanly.
    ok_state = deepcopy(state_at_lr028)
    reducers.reduce_decision_resolution(ok_state, "LR-029", lr029_tx, {})
    assert adp["record_id"] in ok_state["records"][reducers.ADOPTION]

    unsatisfied_state = deepcopy(state_at_lr028)
    unsatisfied_state["reviews"][review_id]["verdict"] = "reject"
    with pytest.raises(IntegrityError, match="W9 resolution's review is not satisfied on the record's hash"):
        reducers.reduce_decision_resolution(unsatisfied_state, "LR-029", lr029_tx, {})

    missing_review_state = deepcopy(state_at_lr028)
    missing_review_state["reviews"].pop(review_id)
    with pytest.raises(IntegrityError, match="W9 resolution's review is not satisfied on the record's hash"):
        reducers.reduce_decision_resolution(missing_review_state, "LR-029", lr029_tx, {})


# --- Analyst rule (§5.3, M-3, §15) ----------------------------------------------------------------------------------


def test_analyst_rule_allows_own_adoption_and_discharge_and_refuses_source_inventory_observer(
    accepted_flow, actors
) -> None:
    forger, records, schemas = accepted_flow
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])
    forger = flows.adoption_recorded(forger, actors, adp, start=70)
    dis = flows.discharge(forger.project_id, actors.analyst, at(90))
    forger = flows.discharge_recorded(forger, actors, dis, start=90)
    state = _replay(forger, schemas)
    assert adp["record_id"] in state["records"][reducers.ADOPTION]
    assert dis["record_id"] in state["records"][reducers.DISCHARGE]

    inv_proposal = {
        "kind": "legacy_source_inventory",
        "actor_id": actors.analyst,
        "record": {"observer_actor_id": actors.observer},
    }
    assert reducers._creator_role_actor(inv_proposal) == actors.observer
    with pytest.raises(IntegrityError, match="W9 analyst is the proposal's creator"):
        reducers._refuse_analyst_creator(inv_proposal, actors.observer)
    for exempt_kind in ("legacy_transition_mapping", reducers.OWNERSHIP, reducers.ADOPTION, reducers.DISCHARGE):
        reducers._refuse_analyst_creator(
            {"kind": exempt_kind, "actor_id": actors.analyst, "record": {}}, actors.analyst
        )


# --- Fixture entries (§5.4, owner point L, R-M5, §15) ----------------------------------------------------------------


def test_fixture_entries_at_request_decision_and_wp9_3_rows(accepted_flow, actors) -> None:
    forger, records, schemas = accepted_flow
    claim_adp = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(70),
        records["family_set"],
        intended_use={"description": "w9-use:claim-evidence/c1", "successor_ref": None},
    )

    # LR-026 missing w9-applicable-fixtures entry.
    no_entry = flows.adoption_recorded(
        forger,
        actors,
        claim_adp,
        tweaks={"LR-026": Tweak(payload={"review_questions": ["Adopt?"]})},
        stop_after="LR-026",
    )
    _refused(no_entry, schemas, "W9 review request must carry one w9-applicable-fixtures entry")

    # LR-026 missing unconditional S-017.
    no_s017 = flows.adoption_recorded(forger, actors, claim_adp, applicable_fixtures=("F-019",), stop_after="LR-026")
    _refused(no_s017, schemas, "W9 review request lacks required fixture S-017")

    # LR-026 claim use missing F-019.
    no_f019 = flows.adoption_recorded(forger, actors, claim_adp, applicable_fixtures=("S-017",), stop_after="LR-026")
    _refused(no_f019, schemas, "W9 review request lacks required fixture F-019")

    # LR-026 manuscript-claims use also requires F-019.
    ms_adp = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(70),
        records["family_set"],
        intended_use={"description": "w9-use:manuscript-claims/P01-B", "successor_ref": None},
    )
    ms_no_f019 = flows.adoption_recorded(forger, actors, ms_adp, applicable_fixtures=("S-017",), stop_after="LR-026")
    _refused(ms_no_f019, schemas, "W9 review request lacks required fixture F-019")

    # LR-026 unlisted fixture (F-006) or unsorted.
    unlisted = flows.adoption_recorded(
        forger, actors, claim_adp, applicable_fixtures=("F-006", "F-019", "S-017"), stop_after="LR-026"
    )
    _refused(unlisted, schemas, "W9 review request lists a fixture LR-029 does not name: F-006")
    unsorted_q = flows.adoption_recorded(
        forger,
        actors,
        claim_adp,
        tweaks={"LR-026": Tweak(payload={"review_questions": ["w9-applicable-fixtures:S-017,F-019"]})},
        stop_after="LR-026",
    )
    _refused(unsorted_q, schemas, "W9 review request w9-applicable-fixtures entry is malformed or not sorted")
    for bare_questions in (["w9-applicable-fixtures:F-019,S-017"], ["   ", "w9-applicable-fixtures:F-019,S-017"]):
        no_question = flows.adoption_recorded(
            forger,
            actors,
            claim_adp,
            tweaks={"LR-026": Tweak(payload={"review_questions": bare_questions})},
            stop_after="LR-026",
        )
        _refused(
            no_question, schemas, "W9 review request carries no review question besides the applicable-fixtures entry"
        )

    # LR-028 fixture set differs from review's applicable set (review approved F-015,F-019,S-017; Decision omits F-015).
    diff_dec = flows.adoption_recorded(
        forger,
        actors,
        claim_adp,
        applicable_fixtures=("F-015", "F-019", "S-017"),
        fixture_refs=[f"w9-fixture:F-019:{new_id('artefact')}", f"w9-fixture:S-017:{new_id('decision')}"],
        stop_after="LR-028",
    )
    _refused(diff_dec, schemas, "W9 Decision proposal fixture set differs from the review's applicable fixtures")

    # LR-028 invalid ref kind (obj_ instead of rev_/art_/dec_), duplicate, unsorted.
    bad_ref_dec = flows.adoption_recorded(
        forger,
        actors,
        claim_adp,
        applicable_fixtures=("F-019", "S-017"),
        fixture_refs=[f"w9-fixture:F-019:{new_id('scope_definition')}", f"w9-fixture:S-017:{new_id('review')}"],
        stop_after="LR-028",
    )
    _refused(bad_ref_dec, schemas, "W9 Decision fixture entry is malformed")

    unsorted_dec = flows.adoption_recorded(
        forger,
        actors,
        claim_adp,
        applicable_fixtures=("F-019", "S-017"),
        fixture_refs=[f"w9-fixture:S-017:{new_id('review')}", f"w9-fixture:F-019:{new_id('review')}"],
        stop_after="LR-028",
    )
    _refused(unsorted_dec, schemas, "W9 Decision fixture entries are not sorted")

    # LR-029 resolution fixture refs differing from proposal refused.
    good_lr028 = flows.adoption_recorded(forger, actors, claim_adp, stop_after="LR-028")
    grant = new_id("authority_grant")
    rev_id = adoption_review_id(claim_adp["record_id"], claim_adp["created_at"])
    lr028_prop = good_lr028.events[-1]["payload"]
    bad_res = flows.resolution(
        "LR-029",
        lr028_prop,
        claim_adp,
        actors.owner,
        grant,
        at(76),
        [rev_id],
        governing_evidence_refs=[
            "W9:LR-029",
            f"w9-subject:{claim_adp['record_id']}",
            f"w9-subject-sha256:{claim_adp['content_hash']}",
            f"w9-fixture:S-017:{new_id('review')}",
        ],
    )
    bad_lr029 = good_lr028.append(
        "ResolveW9AuthorityDecision",
        [
            ("DecisionResolved", claim_adp["decision_ref"]["id"], bad_res),
            ("LegacyAdoptionDecisionRecorded", claim_adp["record_id"], deepcopy(claim_adp)),
        ],
        actor=actors.owner,
        when=at(76),
        grant=grant,
    )
    _refused(bad_lr029, schemas, "W9 Decision resolution governing_evidence_refs is not the required value")

    # WP9.3 row (LR-004) with a 4th ref is STILL refused.
    reg = flows.registration(forger.project_id, actors.analyst, at(95), path="results/fourth.json", file_id="99")
    forged_reg = forger.row("LR-003", reg["record_id"], reg, actor=actors.analyst, when=at(95))
    reg_prop = flows.decision_proposal("LR-004", reg, reg["registration_decision_ref"]["id"], at(96))
    reg_prop["governing_evidence_refs"].append(f"w9-fixture:S-017:{new_id('review')}")
    forged_reg = forged_reg.row(
        "LR-004", reg["registration_decision_ref"]["id"], reg_prop, actor=actors.analyst, when=at(96)
    )
    _refused(forged_reg, schemas, "W9 Decision proposal does not encode its subject")


# --- LR-023 refusals (§6.1 to §6.3, §6.5, §7, §15) ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "expected_message"),
    [
        ("inventory-item", "W9 inventory item observation cannot be adopted"),
        ("families-on-whole-obs", "W9 family adoption requires a json_family_set observation"),
        ("unknown-family", "W9 adoption names a family not in its observation"),
        ("whole-on-family-obs", "W9 whole-file adoption requires a whole_file observation"),
        ("whole-on-json", "W9 whole-file adoption cannot name a .json source"),
        ("unaccepted-obs", "W9 adoption observation has no recorded closed-reference acceptance"),
        ("target-free-claim", "W9 adoption intended_use description is not a permitted use form"),
        ("target-free-manuscript", "W9 adoption intended_use description is not a permitted use form"),
        ("empty-manuscript-key", "W9 adoption manuscript-claims key must be P01-A or P01-B"),
        ("lowercase-paper-key", "W9 adoption manuscript-claims key must be P01-A or P01-B"),
        ("unknown-paper-key", "W9 adoption manuscript-claims key must be P01-A or P01-B"),
        ("bad-claim-key", "W9 adoption use key is malformed"),
        ("bad-task-key", "W9 adoption use key is malformed"),
        ("successor-on-claim", "W9 adoption intended_use successor_ref is not permitted for this use"),
        ("successor-on-manuscript", "W9 adoption intended_use successor_ref is not permitted for this use"),
        ("superseded-obs", "W9 adoption observation is superseded"),
        ("superseded-acc", "W9 adoption observation acceptance is superseded"),
        ("non-task-successor", "W9 adoption intended_use successor_ref is not permitted for this use"),
        ("duplicate-qualifier", "W9 adoption qualifiers_to_discharge repeats a qualifier"),
        ("claim-with-declared-q", "W9 claim-use adoption must carry no qualifiers_to_discharge"),
        ("wrong-consequence-clean", "W9 adoption w5_consequence must be admissible_for_named_use"),
    ],
)
def test_lr023_subject_use_and_qualifier_refusals(accepted_flow, actors, case: str, expected_message: str) -> None:
    forger, records, schemas = accepted_flow
    obs = records["family_set"]
    kw: dict[str, Any] = {}
    if case == "inventory-item":
        obs = records["item"]
    elif case == "families-on-whole-obs":
        obs = records["bin_obs"]
    elif case == "unknown-family":
        kw["subject"] = {"subject_kind": "families", "family_names": ["missing_family"]}
    elif case == "whole-on-family-obs":
        kw["subject"] = {"subject_kind": "whole_file", "rehash_at_use": True}
    elif case == "whole-on-json":
        obs = records["json_whole_obs"]
        kw["subject"] = {"subject_kind": "whole_file", "rehash_at_use": True}
    elif case == "unaccepted-obs":
        obs = records["whole"]
        kw["subject"] = {"subject_kind": "whole_file", "rehash_at_use": True}
    elif case == "target-free-claim":
        kw["intended_use"] = {"description": "w9-use:claim-evidence", "successor_ref": None}
    elif case == "target-free-manuscript":
        kw["intended_use"] = {"description": "w9-use:manuscript-claims", "successor_ref": None}
    elif case == "empty-manuscript-key":
        kw["intended_use"] = {"description": "w9-use:manuscript-claims/", "successor_ref": None}
    elif case == "lowercase-paper-key":
        kw["intended_use"] = {"description": "w9-use:manuscript-claims/p01-a", "successor_ref": None}
    elif case == "unknown-paper-key":
        kw["intended_use"] = {"description": "w9-use:manuscript-claims/P01-C", "successor_ref": None}
    elif case == "bad-claim-key":
        kw["intended_use"] = {"description": "w9-use:claim-evidence/BadKey", "successor_ref": None}
    elif case == "bad-task-key":
        kw["intended_use"] = {"description": "w9-use:task-input/-bad", "successor_ref": None}
    elif case == "successor-on-claim":
        kw["intended_use"] = {"description": "w9-use:claim-evidence/c1", "successor_ref": flows.record_ref(obs)}
    elif case == "successor-on-manuscript":
        kw["intended_use"] = {"description": "w9-use:manuscript-claims/P01-A", "successor_ref": flows.record_ref(obs)}
    elif case in {"superseded-obs", "superseded-acc"}:
        target = obs if case == "superseded-obs" else records["acceptance"]
        replacing = (
            flows.observation(forger.project_id, actors.observer, at(81), records["registration"], PIN, count=2)
            if case == "superseded-obs"
            else flows.acceptance(forger.project_id, actors.analyst, at(81), [obs])
        )
        sup_id = new_id("scope_definition")
        rev_id = new_id("review")
        dec_id = new_id("decision")
        grant = new_id("authority_grant")
        rec = flows.stamp(
            {
                "schema_id": "ars://legacy/legacy-record-supersession",
                "schema_version": "1.0.0",
                "record_id": sup_id,
                "record_revision": 1,
                "supersedes_revision": None,
                "project_id": forger.project_id,
                "created_at": at(82),
                "created_by_actor_id": actors.analyst,
                "content_hash": "0" * 64,
                "superseded_ref": flows.record_ref(target),
                "replacing_ref": flows.record_ref(replacing),
                "reason": "superseded before adoption",
                "reviewer_ref": pre_assigned_ref("review", rev_id, sup_id),
                "decision_ref": pre_assigned_ref("decision", dec_id, sup_id),
            }
        )
        prop = flows.decision_proposal("LR-059", rec, dec_id, at(83))
        res = flows.resolution("LR-060", prop, rec, actors.owner, grant, at(84), [rev_id])
        sup_req = flows.review_request("LR-057", rec, rev_id, actors.reviewer, at(82.2))
        sup_verdict = flows.verdict(sup_req, at(82.2), actors.reviewer)
        forger = (
            forger.row("LR-056", sup_id, rec, actor=actors.analyst, when=at(82))
            .row("LR-057", rev_id, sup_req, actor=actors.analyst, when=at(82.2))
            .row("LR-058", rev_id, sup_verdict, actor=actors.reviewer, when=at(82.4))
            .row("LR-059", dec_id, prop, actor=actors.analyst, when=at(83))
            .append(
                "ResolveW9AuthorityDecision",
                [("DecisionResolved", dec_id, res), ("LegacyRecordSupersessionRecorded", sup_id, rec)],
                actor=actors.owner,
                when=at(84),
                grant=grant,
            )
        )
        adp = flows.adoption(forger.project_id, actors.analyst, at(85), obs, **kw)
        forged = forger.row("LR-023", adp["record_id"], adp, actor=actors.analyst, when=at(85))
        _refused(
            forged,
            schemas,
            expected_message,
            routed_rows=LEGACY_ROUTED_ROWS | {*(f"LR-{n:03d}" for n in range(56, 61))},
        )
        return
    elif case == "non-task-successor":
        kw["intended_use"] = {"description": "w9-use:task-input/t1", "successor_ref": flows.record_ref(obs)}
    elif case == "duplicate-qualifier":
        q = _open_finding(obs)
        kw["qualifiers_to_discharge"] = [q, q]
    elif case == "claim-with-declared-q":
        kw["qualifiers_to_discharge"] = [_open_finding(obs)]
    elif case == "wrong-consequence-clean":
        kw["w5_consequence"] = "task_input_with_open_findings"

    adp = flows.adoption(forger.project_id, actors.analyst, at(85), obs, **kw)
    forged = forger.row("LR-023", adp["record_id"], adp, actor=actors.analyst, when=at(85))
    _refused(forged, schemas, expected_message)


def test_lr023_qualifiers_and_consequence_with_open_finding(base, actors) -> None:  # noqa: F811
    forger, schemas = base
    forger, obs = _accepted_task_obs_with_finding(forger, actors)
    q = obs["qualifiers"][0]

    # Claim / manuscript uses with open finding refused.
    for desc in ("w9-use:claim-evidence/c1", "w9-use:manuscript-claims/P01-A"):
        bad = flows.adoption(
            forger.project_id, actors.analyst, at(40), obs, intended_use={"description": desc, "successor_ref": None}
        )
        _refused(
            forger.row("LR-023", bad["record_id"], bad, actor=actors.analyst, when=at(40)),
            schemas,
            "W9 claim-use adoption refused while observation has open review findings",
        )

    # Task-input missing finding or wrong consequence refused.
    missing_q = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(40),
        obs,
        intended_use={"description": "w9-use:task-input/calib", "successor_ref": None},
        w5_consequence="task_input_with_open_findings",
        qualifiers_to_discharge=[],
    )
    _refused(
        forger.row("LR-023", missing_q["record_id"], missing_q, actor=actors.analyst, when=at(40)),
        schemas,
        "W9 task-input adoption qualifiers_to_discharge must equal observation open review findings",
    )

    bad_conseq = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(40),
        obs,
        intended_use={"description": "w9-use:task-input/calib", "successor_ref": None},
        w5_consequence="admissible_for_named_use",
        qualifiers_to_discharge=[q],
    )
    _refused(
        forger.row("LR-023", bad_conseq["record_id"], bad_conseq, actor=actors.analyst, when=at(40)),
        schemas,
        "W9 adoption w5_consequence must be task_input_with_open_findings",
    )

    # Valid task-input with finding replays clean.
    good = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(40),
        obs,
        intended_use={"description": "w9-use:task-input/calib", "successor_ref": None},
        w5_consequence="task_input_with_open_findings",
        qualifiers_to_discharge=[q],
    )
    good_forger = flows.adoption_recorded(forger, actors, good, start=40)
    state = _replay(good_forger, schemas)
    assert good["record_id"] in state["records"][reducers.ADOPTION]


def test_lr023_refuses_adoption_suspended_at_birth(accepted_flow, actors) -> None:
    """§6.5, §7 (review m-12): a later overlapping observation before LR-023 suspends the adoption at birth."""
    forger, records, schemas = accepted_flow
    re_obs = flows.observation(
        forger.project_id,
        actors.observer,
        at(66),
        records["registration"],
        PIN,
        count=2,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(records["table"]),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", PIN)],
    )
    forger = forger.row("LR-015", re_obs["record_id"], re_obs, actor=actors.observer, when=at(66))
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])
    _refused(
        forger.row("LR-023", adp["record_id"], adp, actor=actors.analyst, when=at(70)),
        schemas,
        "W9 adoption would be suspended at proposal: later_observation",
    )


def test_lr029_refuses_adoption_suspended_after_proposal(accepted_flow, actors) -> None:
    """§6.5: if source is re-observed after LR-023 (or becomes stale) before LR-029, resolution refuses."""
    forger, records, schemas = accepted_flow
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])
    through_lr028 = flows.adoption_recorded(forger, actors, adp, start=70, stop_after="LR-028")
    re_obs = flows.observation(
        through_lr028.project_id,
        actors.observer,
        at(75.5),
        records["registration"],
        PIN,
        count=2,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(records["table"]),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", PIN)],
    )
    with_later_obs = through_lr028.row("LR-015", re_obs["record_id"], re_obs, actor=actors.observer, when=at(75.5))
    lr028_prop = through_lr028.events[-1]["payload"]
    rev_id = adoption_review_id(adp["record_id"], adp["created_at"])
    grant = new_id("authority_grant")
    resolved = flows.resolution("LR-029", lr028_prop, adp, actors.owner, grant, at(76), [rev_id])
    bad = with_later_obs.append(
        "ResolveW9AuthorityDecision",
        [
            ("DecisionResolved", adp["decision_ref"]["id"], resolved),
            ("LegacyAdoptionDecisionRecorded", adp["record_id"], deepcopy(adp)),
        ],
        actor=actors.owner,
        when=at(76),
        grant=grant,
    )
    _refused(bad, schemas, "W9 adoption is suspended at resolution: later_observation")


# --- LR-024 to LR-027 eligibility & C-m1 controls (§5.5, §15) --------------------------------------------------------


def test_lr024_and_lr025_eligibility_decision_controls(accepted_flow, actors) -> None:
    forger, records, schemas = accepted_flow
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])

    # Accepted before any review exists.
    before_review = flows.adoption_recorded(forger, actors, adp, start=70, stop_after="LR-025")
    state = _replay(before_review, schemas)
    elig_id = adoption_eligibility_decision_id(adp["record_id"], adp["created_at"])
    assert state["decisions"][elig_id]["resolve_row"] == "LR-025"
    assert state["decisions"][elig_id]["selected_option"] == "accept"
    assert adoption_review_id(adp["record_id"], adp["created_at"]) not in state["reviews"]

    # 7 refs refused.
    prop7 = flows.eligibility_proposal(adp, at(71))
    prop7["governing_evidence_refs"].pop()
    _refused(
        forger.row("LR-023", adp["record_id"], adp, actor=actors.analyst, when=at(70)).row(
            "LR-024", elig_id, prop7, actor=actors.analyst, when=at(71)
        ),
        schemas,
        "W9 eligibility Decision proposal must carry exactly 8 governing_evidence_refs",
    )

    # Non-independent grade refused.
    bad_grade = flows.adoption_recorded(
        forger, actors, adp, start=70, eligibility={**flows.ELIGIBILITY, "grade": "self"}, stop_after="LR-024"
    )
    _refused(bad_grade, schemas, "W9 eligibility Decision grade must be independent")

    # Non-derived eligibility ID refused.
    wrong_elig_id = new_id("decision")
    bad_id_prop = flows.eligibility_proposal(adp, at(71), new_decision_id=wrong_elig_id)
    _refused(
        forger.row("LR-023", adp["record_id"], adp, actor=actors.analyst, when=at(70)).row(
            "LR-024", wrong_elig_id, bad_id_prop, actor=actors.analyst, when=at(71)
        ),
        schemas,
        "W9 eligibility Decision ID is not the derived eligibility Decision ID",
    )

    # Stale subject hash refused.
    stale_hash = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={
            "LR-024": Tweak(
                payload={
                    "governing_evidence_refs": [
                        "W9:LR-024",
                        f"w9-subject:{adp['record_id']}",
                        f"w9-subject-sha256:{'0' * 64}",
                        "w9-eligible-session:s",
                        "w9-eligible-family:f",
                        "w9-eligible-version:v",
                        "w9-eligible-profile:p",
                        "w9-eligible-grade:independent",
                    ]
                }
            )
        },
        stop_after="LR-024",
    )
    _refused(stale_hash, schemas, "W9 Decision proposal subject hash is not the proposal's current hash")

    # LR-025 with a record event refused by transaction shape (and directly by reducer).
    with_lr024 = flows.adoption_recorded(forger, actors, adp, start=70, stop_after="LR-024")
    elig_prop = with_lr024.events[-1]["payload"]
    grant = new_id("authority_grant")
    with_extra_rec = with_lr024.append(
        "ResolveW9AuthorityDecision",
        [
            ("DecisionResolved", elig_id, flows.eligibility_resolution(elig_prop, adp, actors.owner, grant, at(72))),
            ("LegacyAdoptionDecisionRecorded", adp["record_id"], deepcopy(adp)),
        ],
        actor=actors.owner,
        when=at(72),
        grant=grant,
    )
    _refused(with_extra_rec, schemas, "W9 transaction differs from accepted LR-025")
    with pytest.raises(IntegrityError, match="W9 eligibility resolution must not emit a record"):
        reducers._check_eligibility_resolution(
            {}, {"subject": (adp["record_id"], adp["content_hash"])}, [{"payload": {}}, {"payload": {}}]
        )

    # LR-025 resolved reject passes LR-025, then LR-026 refuses.
    rejected_elig = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-025": Tweak(payload={"selected_option": "reject"})},
        stop_after="LR-025",
    )
    assert _replay(rejected_elig, schemas)["decisions"][elig_id]["selected_option"] == "reject"
    _refused(
        flows.adoption_recorded(
            forger,
            actors,
            adp,
            start=70,
            tweaks={"LR-025": Tweak(payload={"selected_option": "reject"})},
            stop_after="LR-026",
        ),
        schemas,
        "W9 adoption review requires an accepted eligibility Decision",
    )

    # LR-025 after expiry refused.
    expired_elig = flows.adoption_recorded(
        forger, actors, adp, start=70, tweaks={"LR-025": Tweak(minutes=32 * 24 * 60)}, stop_after="LR-025"
    )
    _refused(expired_elig, schemas, "W9 Decision resolved after it expired")


def test_lr026_and_lr027_session_profile_model_and_w9c_controls(accepted_flow, actors) -> None:
    forger, records, schemas = accepted_flow
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])

    # LR-026 before LR-025 resolves refused.
    no_elig_res = flows.adoption_recorded(forger, actors, adp, start=70, stop_after="LR-024")
    rev_id = adoption_review_id(adp["record_id"], adp["created_at"])
    req = flows.review_request(
        "LR-026",
        adp,
        rev_id,
        actors.reviewer,
        at(72),
        review_questions=["Adopt?", "w9-applicable-fixtures:F-019,S-017"],
        required_evidence_refs=[
            "w9-analyst-session:session-analyst",
            f"w9-eligible-session:{flows.ELIGIBILITY['session']}",
        ],
    )
    _refused(
        no_elig_res.row("LR-026", rev_id, req, actor=actors.analyst, when=at(72)),
        schemas,
        "W9 adoption review requires an accepted eligibility Decision",
    )

    # LR-026 naming another session refused.
    wrong_sess_req = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={
            "LR-026": Tweak(
                payload={
                    "required_evidence_refs": [
                        "w9-analyst-session:session-analyst",
                        "w9-eligible-session:other-session",
                    ]
                }
            )
        },
        stop_after="LR-026",
    )
    _refused(
        wrong_sess_req, schemas, "W9 adoption review request eligible session differs from the eligibility Decision"
    )

    # Fix 1 (CodeRabbit #439): LR-026 refuses analyst_session == eligible_session before reserving review.
    same_sess_req = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={
            "LR-026": Tweak(
                payload={
                    "required_evidence_refs": [
                        f"w9-analyst-session:{flows.ELIGIBILITY['session']}",
                        f"w9-eligible-session:{flows.ELIGIBILITY['session']}",
                    ]
                }
            )
        },
        stop_after="LR-026",
    )
    _refused(same_sess_req, schemas, "W9 adoption review request names the analyst session as the eligible session")

    # C-m1: LR-027 from analyst session refused, from third non-eligible session refused, eligible session passes.
    analyst_sess_verdict = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-027": Tweak(payload={"reviewer_session": "session-analyst"})},
        stop_after="LR-027",
    )
    _refused(analyst_sess_verdict, schemas, "W9 reviewer session is a session the request records")

    third_sess_verdict = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-027": Tweak(payload={"reviewer_session": "session-third"})},
        stop_after="LR-027",
    )
    _refused(third_sess_verdict, schemas, "W9 adoption verdict session differs from the eligible session")

    # Profile & model metadata checks at LR-027.
    bad_profile = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-027": Tweak(payload={"reviewer_profile": "wrong-profile"})},
        stop_after="LR-027",
    )
    _refused(bad_profile, schemas, "W9 verdict reviewer_profile is not the derived value")

    bad_model = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-027": Tweak(payload={"reviewer_model_metadata": "other@v1"})},
        stop_after="LR-027",
    )
    _refused(bad_model, schemas, "W9 adoption verdict reviewer_model_metadata differs from the eligibility Decision")

    # W9-C20, W9-C21, W9-C22.
    w9c20 = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-026": Tweak(payload={"reviewer_capability": [actors.analyst]})},
        stop_after="LR-026",
    )
    _refused(w9c20, schemas, "W9 reviewer is the proposal's creator, author or the requesting analyst")

    w9c21 = flows.adoption_recorded(
        forger, actors, adp, start=70, tweaks={"LR-027": Tweak(actor=actors.reproducer)}, stop_after="LR-027"
    )
    _refused(w9c21, schemas, "W9 verdict is not recorded by the reviewer the request named")

    w9c22 = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-026": Tweak(payload={"subject_hashes": ["0" * 64]})},
        stop_after="LR-026",
    )
    _refused(w9c22, schemas, "W9 review request subject hash is not the proposal's current hash")


# --- LR-030 to LR-034 discharge replay controls (§8, W9-C20..C25, §15) -----------------------------------------------


def test_discharge_replay_uniqueness_blob_and_w9c_controls(accepted_flow, actors) -> None:
    forger, _, schemas = accepted_flow
    d1 = flows.discharge(forger.project_id, actors.analyst, at(90), item_kind="a001_item", item_id="A001-01")
    open_d1 = flows.discharge_recorded(forger, actors, d1, start=90, stop_after="LR-030")

    # Second open relation for same (item_kind, item_id) refused.
    d1_dup = flows.discharge(forger.project_id, actors.analyst, at(91), item_kind="a001_item", item_id="A001-01")
    _refused(
        open_d1.row("LR-030", d1_dup["record_id"], d1_dup, actor=actors.analyst, when=at(91)),
        schemas,
        "W9 discharge relation already open for this legacy item",
    )

    # Different item_kind with same item_id is admitted.
    d_other_kind = flows.discharge(forger.project_id, actors.analyst, at(91), item_kind="audit_hole", item_id="A001-01")
    assert (
        d_other_kind["record_id"]
        in _replay(flows.discharge_recorded(open_d1, actors, d_other_kind, start=91), schemas)["records"][
            reducers.DISCHARGE
        ]
    )

    # Once d1 is recorded at LR-034, second LR-030 for same (item_kind, item_id) refused.
    recorded_d1 = flows.discharge_recorded(forger, actors, d1, start=90)
    d1_after = flows.discharge(forger.project_id, actors.analyst, at(96), item_kind="a001_item", item_id="A001-01")
    _refused(
        recorded_d1.row("LR-030", d1_after["record_id"], d1_after, actor=actors.analyst, when=at(96)),
        schemas,
        "W9 legacy item already has a recorded discharge relation",
    )

    # After first proposal lapses (31 days), a new proposal for the same item is admitted.
    d1_after_lapse = flows.discharge(
        forger.project_id, actors.analyst, at(90 + 31 * 24 * 60), item_kind="a001_item", item_id="A001-01"
    )
    assert (
        d1_after_lapse["record_id"]
        in _replay(flows.discharge_recorded(open_d1, actors, d1_after_lapse, start=90 + 31 * 24 * 60), schemas)[
            "records"
        ][reducers.DISCHARGE]
    )

    # Missing or invalid w9-open-items-blob at LR-033, and non-empty fixtures at LR-031/LR-033, refused.
    d2 = flows.discharge(forger.project_id, actors.analyst, at(100), item_kind="review_finding", item_id="RF-9")
    bad_blob = flows.discharge_recorded(
        forger, actors, d2, start=100, open_items_blob="not-a-sha1", stop_after="LR-033"
    )
    _refused(bad_blob, schemas, "W9 discharge Decision must carry one valid w9-open-items-blob entry")

    non_empty_q = flows.discharge_recorded(
        forger,
        actors,
        d2,
        start=100,
        tweaks={"LR-031": Tweak(payload={"review_questions": ["w9-applicable-fixtures:S-017"]})},
        stop_after="LR-031",
    )
    _refused(non_empty_q, schemas, "W9 review request lists a fixture LR-034 does not name: S-017")
    for bare_questions in (["w9-applicable-fixtures:"], ["\t ", "w9-applicable-fixtures:"]):
        no_question = flows.discharge_recorded(
            forger,
            actors,
            d2,
            start=100,
            tweaks={"LR-031": Tweak(payload={"review_questions": bare_questions})},
            stop_after="LR-031",
        )
        _refused(
            no_question, schemas, "W9 review request carries no review question besides the applicable-fixtures entry"
        )

    # W9-C25 id collision on discharge pre-assigned ref.
    taken_dec = d1["decision_ref"]["id"]
    colliding = flows.discharge(forger.project_id, actors.analyst, at(98), item_kind="audit_hole", item_id="H-2")
    colliding["decision_ref"] = pre_assigned_ref("decision", taken_dec, colliding["record_id"])
    flows.stamp(colliding)
    _refused(
        recorded_d1.row("LR-030", colliding["record_id"], colliding, actor=actors.analyst, when=at(98)),
        schemas,
        "W9 pre-assigned ID is already claimed or reserved",
    )


def test_flow_helpers_apply_lr023_and_lr030_payload_tweaks_and_preserve_bad_hash(accepted_flow, actors) -> None:
    """Fix 6 (CodeRabbit #439): adoption_recorded and discharge_recorded apply first-row payload tweaks."""
    forger, records, schemas = accepted_flow

    adp = flows.adoption(forger.project_id, actors.analyst, at(70), records["family_set"])
    bad_consequence = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-023": Tweak(payload={"w5_consequence": "task_input_with_open_findings"})},
        stop_after="LR-023",
    )
    _refused(bad_consequence, schemas, "W9 adoption w5_consequence must be admissible_for_named_use")

    bad_adp_hash = flows.adoption_recorded(
        forger,
        actors,
        adp,
        start=70,
        tweaks={"LR-023": Tweak(payload={"content_hash": "0" * 64})},
        stop_after="LR-023",
    )
    _refused(bad_adp_hash, schemas, "W9 record content_hash is not the hash of its content")

    d1 = flows.discharge(forger.project_id, actors.analyst, at(90), item_kind="a001_item", item_id="A001-01")
    recorded_d1 = flows.discharge_recorded(forger, actors, d1, start=90)
    d2 = flows.discharge(forger.project_id, actors.analyst, at(96), item_kind="a001_item", item_id="A001-02")
    dup_item = flows.discharge_recorded(
        recorded_d1,
        actors,
        d2,
        start=96,
        tweaks={"LR-030": Tweak(payload={"legacy_item": {"item_kind": "a001_item", "item_id": "A001-01"}})},
        stop_after="LR-030",
    )
    _refused(dup_item, schemas, "W9 legacy item already has a recorded discharge relation")

    bad_dis_hash = flows.discharge_recorded(
        forger,
        actors,
        d2,
        start=96,
        tweaks={"LR-030": Tweak(payload={"content_hash": "0" * 64})},
        stop_after="LR-030",
    )
    _refused(bad_dis_hash, schemas, "W9 record content_hash is not the hash of its content")


# --- W9-T9 forged-ledger supersession & LR-061 mismatch (test route set, §7, §15) ------------------------------------


def test_w9_t9_forged_ledger_supersession_and_mismatch_suspend_adoption(accepted_flow, actors) -> None:
    """§7, §15: WP9.6 supersession (obs, acceptance, adoption) and WP9.7 mismatch (LR-061) suspend the adoption."""
    forger, records, schemas = accepted_flow
    test_routes = LEGACY_ROUTED_ROWS | {*(f"LR-{n:03d}" for n in range(56, 62))}
    obs = records["family_set"]
    adp = flows.adoption(forger.project_id, actors.analyst, at(70), obs)
    forger = flows.adoption_recorded(forger, actors, adp, start=70)

    def _supersede(base_forger: Forger, target: dict[str, Any], replacing: dict[str, Any], start_m: float) -> Forger:
        sup_id = new_id("scope_definition")
        rev_id = new_id("review")
        dec_id = new_id("decision")
        rec = flows.stamp(
            {
                "schema_id": "ars://legacy/legacy-record-supersession",
                "schema_version": "1.0.0",
                "record_id": sup_id,
                "record_revision": 1,
                "supersedes_revision": None,
                "project_id": base_forger.project_id,
                "created_at": at(start_m),
                "created_by_actor_id": actors.analyst,
                "content_hash": "0" * 64,
                "superseded_ref": flows.record_ref(target),
                "replacing_ref": flows.record_ref(replacing),
                "reason": "superseded in test",
                "reviewer_ref": pre_assigned_ref("review", rev_id, sup_id),
                "decision_ref": pre_assigned_ref("decision", dec_id, sup_id),
            }
        )
        prop = flows.decision_proposal("LR-059", rec, dec_id, at(start_m + 1))
        grant = new_id("authority_grant")
        res = flows.resolution("LR-060", prop, rec, actors.owner, grant, at(start_m + 2), [rev_id])
        sup_req = flows.review_request("LR-057", rec, rev_id, actors.reviewer, at(start_m + 0.2))
        sup_verdict = flows.verdict(sup_req, at(start_m + 0.2), actors.reviewer)
        return (
            base_forger.row("LR-056", sup_id, rec, actor=actors.analyst, when=at(start_m))
            .row("LR-057", rev_id, sup_req, actor=actors.analyst, when=at(start_m + 0.2))
            .row("LR-058", rev_id, sup_verdict, actor=actors.reviewer, when=at(start_m + 0.4))
            .row("LR-059", dec_id, prop, actor=actors.analyst, when=at(start_m + 1))
            .append(
                "ResolveW9AuthorityDecision",
                [("DecisionResolved", dec_id, res), ("LegacyRecordSupersessionRecorded", sup_id, rec)],
                actor=actors.owner,
                when=at(start_m + 2),
                grant=grant,
            )
        )

    # 1. Supersede observation -> observation_superseded.
    rep_obs = flows.observation(
        forger.project_id,
        actors.observer,
        at(81),
        records["registration"],
        PIN,
        count=2,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(records["table"]),
            "family_names": ["other"],
        },
        families=[flows.signed_family("other", PIN)],
    )
    f_obs = _supersede(
        forger.row("LR-015", rep_obs["record_id"], rep_obs, actor=actors.observer, when=at(81)), obs, rep_obs, 82
    )
    s_obs = _replay(f_obs, schemas, routed_rows=test_routes)
    assert projection_read.adoption_status(s_obs, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "observation_superseded",
    }

    # 2. Supersede closed-reference acceptance -> acceptance_superseded (WP9.7 LR-022 not yet routed for 2nd LR-016).
    rep_acc = flows.acceptance(forger.project_id, actors.analyst, at(81), [records["family_set"]])
    f_acc = _supersede(forger, records["acceptance"], rep_acc, 86)
    s_acc = _replay(f_acc, schemas, routed_rows=test_routes)
    assert projection_read.adoption_status(s_acc, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "acceptance_superseded",
    }

    # 3. Supersede adoption itself -> adoption_superseded.
    rep_adp = flows.adoption(forger.project_id, actors.analyst, at(81), obs)
    f_adp = flows.adoption_recorded(forger, actors, rep_adp, start=81)
    f_adp = _supersede(f_adp, adp, rep_adp, 88)
    s_adp = _replay(f_adp, schemas, routed_rows=test_routes)
    assert projection_read.adoption_status(s_adp, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "adoption_superseded",
    }

    # 4. LR-061 use-time mismatch -> use_mismatch.
    mismatch_id = new_id("scope_definition")
    mismatch = flows.stamp(
        {
            "schema_id": "ars://legacy/legacy-adoption-use-mismatch",
            "schema_version": "1.0.0",
            "record_id": mismatch_id,
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": forger.project_id,
            "created_at": at(82),
            "created_by_actor_id": actors.analyst,
            "content_hash": "0" * 64,
            "adoption_ref": flows.record_ref(adp),
            "successor_task_ref": {"id": new_id("task"), "record_revision": 1, "content_hash": "a" * 64},
            "expected_sha256": "a" * 64,
            "observed_sha256": "b" * 64,
            "observed_byte_length": 12,
            "detected_at": at(82),
            "guard_actor_id": actors.analyst,
        }
    )
    f_mis = forger.row("LR-061", mismatch_id, mismatch, actor=actors.analyst, when=at(82))
    s_mis = _replay(f_mis, schemas, routed_rows=test_routes)
    assert projection_read.adoption_status(s_mis, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "use_mismatch",
    }


def test_flow_builders_pass_explicit_empty_dicts_to_schema(accepted_flow, actors) -> None:
    """Fix 8 (CodeRabbit #439 round 2): explicit {} is preserved and refused at schema validation."""
    forger, records, schemas = accepted_flow
    obs = records["family_set"]

    # Negative controls: default None fills valid fields that pass LR-023 and LR-030.
    ok_adp = flows.adoption(forger.project_id, actors.analyst, at(70), obs)
    assert (
        ok_adp["record_id"]
        in _replay(forger.row("LR-023", ok_adp["record_id"], ok_adp, actor=actors.analyst, when=at(70)), schemas)[
            "proposals"
        ]
    )
    ok_dis = flows.discharge(forger.project_id, actors.analyst, at(90))
    assert (
        ok_dis["record_id"]
        in _replay(forger.row("LR-030", ok_dis["record_id"], ok_dis, actor=actors.analyst, when=at(90)), schemas)[
            "proposals"
        ]
    )

    empty_sub = flows.adoption(forger.project_id, actors.analyst, at(71), obs, subject={})
    empty_use = flows.adoption(forger.project_id, actors.analyst, at(72), obs, intended_use={})
    empty_ref = flows.discharge(forger.project_id, actors.analyst, at(91), successor_result_ref={})
    assert empty_sub["subject"] == {}
    assert empty_use["intended_use"] == {}
    assert empty_ref["successor_result_ref"] == {}

    for row, rec, cause_hint in (
        ("LR-023", empty_sub, "subject:"),
        ("LR-023", empty_use, "intended_use:"),
        ("LR-030", empty_ref, "successor_result_ref:"),
    ):
        with pytest.raises(IntegrityError, match="W9 event payload does not validate against its record schema") as exc:
            _replay(forger.row(row, rec["record_id"], rec, actor=actors.analyst, when=at(92)), schemas)
        assert cause_hint in str(exc.value.__cause__)
