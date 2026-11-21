# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §§10–15, §19 O/K, §26; P-086, P-087)
# Purpose: forged-ledger replay and unit checks for WP9.4-2 (LR-035, LR-039, LR-040 to LR-055, K1-4, O, P-087 item 6, R7-M2).
"""WP9.4-2 replay and unit controls on forged scratch ledgers (P-086, P-087)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy import projection_read
from research_system.legacy.records import (
    citation_status_record_id,
    derived_id,
    pre_assigned_ref,
    utc_milliseconds,
)
from research_system.legacy.replay import reducers
from research_system.legacy.replay.driver import replay_legacy
from research_system.legacy.routes import LEGACY_ROUTED_ROWS, LEGACY_ROW_ROUTES
from research_system.legacy.segmentation import segment
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_legacy_runtime import _genesis_command, _store
from tests.research_system.integration.w9_flows import Actors, Forger, Tweak, at

ALL_ROWS = frozenset(LEGACY_ROW_ROUTES)

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _owner(events: tuple[dict[str, Any], ...]) -> str:
    return next(e["actor_id"] for e in events if e["command_type"] == "ImportAcceptedW9CatalogueGenesis")


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> tuple[tuple[dict[str, Any], ...], Any]:
    tmp_path = tmp_path_factory.mktemp("w9-wp9-4-2-replay")
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    return tuple(harness.ledger.iter_events()), harness.schemas


@pytest.fixture
def actors(base) -> Actors:
    return Actors(owner=_owner(base[0]))


def _replay(
    forger: Forger,
    schemas: Any,
    *,
    pin: dict[str, Any] | None = None,
    routed_rows: frozenset[str] = flows.TEST_FULL_ROUTES,
    **kwargs: Any,
) -> dict[str, Any]:
    if pin is not None:
        kwargs.setdefault("pinned_signatures", (pin,))
    return replay_legacy(forger.events, schemas=schemas, routed_rows=routed_rows, **kwargs)


def _refused(
    forger: Forger,
    schemas: Any,
    message: str,
    *,
    pin: dict[str, Any] | None = None,
    routed_rows: frozenset[str] = flows.TEST_FULL_ROUTES,
    **kwargs: Any,
) -> None:
    with pytest.raises(IntegrityError, match=message):
        _replay(forger, schemas, pin=pin, routed_rows=routed_rows, **kwargs)


# --- LR-035: ordinary paper root creation (§10.1) -------------------------------------------------------------------


def test_lr035_positive_and_refusals(base, actors: Actors) -> None:
    events, schemas = base
    forger = flows.Forger(events)

    # Without LR-022 (and on production routes where LR-022 is unrouted), LR-035 refuses.
    no_pilot, root = flows.paper_root_created(forger, actors, start=10, paper_key="P01-A")
    _refused(no_pilot, schemas, r"W9 LR-035 requires a passed integration-pilot outcome Decision \(LR-022\)")
    _refused(
        no_pilot,
        schemas,
        r"W9 LR-035 requires a passed integration-pilot outcome Decision \(LR-022\)",
        routed_rows=LEGACY_ROUTED_ROWS,
    )

    # Missed option or wrong decision_kind refuses.
    missed = flows.pilot_outcome_passed(forger, actors, start=5, selected_option="missed")
    missed_root, _ = flows.paper_root_created(missed, actors, start=10, paper_key="P01-A")
    _refused(missed_root, schemas, r"W9 LR-035 requires a passed integration-pilot outcome Decision \(LR-022\)")

    wrong_kind = flows.pilot_outcome_passed(forger, actors, start=5, decision_kind="eligibility")
    wrong_kind_root, _ = flows.paper_root_created(wrong_kind, actors, start=10, paper_key="P01-A")
    _refused(wrong_kind_root, schemas, r"W9 LR-035 requires a passed integration-pilot outcome Decision \(LR-022\)")

    # Passed LR-022 + test routes records LR-035; production routes still refuse even with LR-022 forged.
    passed = flows.pilot_outcome_passed(forger, actors, start=5)
    ok_forger, root_rec = flows.paper_root_created(passed, actors, start=10, paper_key="P01-A")
    state = _replay(ok_forger, schemas)
    assert root_rec["record_id"] in state["records"][reducers.PAPER_ROOT]
    with pytest.raises(IntegrityError, match=r"W9 row not routed in this version: LR-021 \(WP9\.7\)"):
        _replay(ok_forger, schemas, routed_rows=LEGACY_ROUTED_ROWS)

    # Duplicate paper_key refuses.
    dup, _ = flows.paper_root_created(ok_forger, actors, start=15, paper_key="P01-A")
    _refused(dup, schemas, "W9 paper root already exists for this paper_key")

    # Non-null recovery refuses at LR-038 (assign_row) and at _check_paper_root_lr035 unit guard.
    rec_payload = flows.paper_root_record(
        passed.project_id,
        actors.analyst,
        at(10),
        paper_key="P01-A",
        recovery={
            "predecessor_root_ref": flows.record_ref(root),
            "recovery_decision_ref": {
                "id": new_id("decision"),
                "record_revision": 1,
                "content_hash": "0" * 64,
            },
        },
    )
    rec_root = passed.row("LR-038", rec_payload["record_id"], rec_payload, actor=actors.analyst, when=at(10))
    _refused(rec_root, schemas, r"W9 row not routed in this version: LR-038 \(WP9\.6\)")
    with pytest.raises(IntegrityError, match="W9 LR-035 refuses a recovery paper root"):
        reducers._check_paper_root_lr035(
            reducers.new_legacy_state(),
            rec_payload,
            {
                "actor_id": actors.analyst,
                "occurred_at": at(10),
                "stream_id": rec_payload["record_id"],
                "stream_version": 1,
                "project_id": passed.project_id,
            },
            {},
        )


# --- LR-039: paper citation status (§5.6, §11.3) ---------------------------------------------------------------------


def test_lr039_positive_unequal_hashes_chain_and_controls(base, actors: Actors) -> None:
    events, _ = base
    _, schemas_events = base
    forger, ctx = flows.full_path_prerequisites(events)
    schemas = schemas_events
    pin = ctx["pin"]
    root = ctx["paper_root"]
    obs_res = ctx["obs_res"]
    adp = ctx["adoption"]
    first_status = ctx["citation_status"]

    # Derived ID check matches records.citation_status_record_id.
    expected_id = citation_status_record_id(
        root["record_id"],
        None,
        first_status["cited_family_set_sha256"],
        first_status["derivation"]["extractor_output_sha256"],
        first_status["derivation"]["reviewer_derivation_sha256"],
        root["created_at"],
    )
    assert first_status["record_id"] == expected_id
    assert expected_id == derived_id(
        "obj",
        (
            f"w9-citation-status:{root['record_id']}:none:"
            f"{first_status['cited_family_set_sha256']}:"
            f"{first_status['derivation']['extractor_output_sha256']}:"
            f"{first_status['derivation']['reviewer_derivation_sha256']}"
        ),
        utc_milliseconds(root["created_at"]),
    )
    state = _replay(forger, schemas, pin=pin)
    assert state["current_citation_status_by_root"] == {root["record_id"]: first_status["record_id"]}

    # Unequal derivation hashes ARE admitted at LR-039 (and blocked later at LR-054), as is an unadopted family.
    forger_b, ctx_b = flows.full_path_prerequisites(events, actors=actors, paper_key="P01-B")
    # Build status manually with unequal hashes & an extra unadopted observation of whole-file member.
    obs_mem = ctx_b["obs_member"]
    unequal = flows.citation_status_record(
        forger_b.project_id,
        actors.reviewer,
        at(107),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            },
            {
                "observation_ref": flows.record_ref(obs_mem),
                "family_name": "whole_file",
                "status": "unadopted",
                "adoption_ref": None,
            },
        ],
        extractor_output_sha256="b" * 64,
        reviewer_derivation_sha256="c" * 64,
        supersedes_status=ctx_b["citation_status"],
    )
    f_unequal = forger_b.row("LR-039", unequal["record_id"], unequal, actor=actors.reviewer, when=at(107))
    st_unequal = _replay(f_unequal, schemas, pin=ctx_b["pin"])
    assert st_unequal["current_citation_status_by_root"][ctx_b["paper_root"]["record_id"]] == unequal["record_id"]
    assert ctx_b["citation_status"]["record_id"] in st_unequal["reference_edges"][unequal["record_id"]]

    # T6: stale supersedes_status_ref naming older status after unequal is current, with unequal's revision and hash.
    stale_id_ref = flows.citation_status_record(
        f_unequal.project_id,
        actors.reviewer,
        at(108),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            }
        ],
        supersedes_status=unequal,
    )
    stale_id_ref["supersedes_status_ref"]["id"] = ctx_b["citation_status"]["record_id"]
    stale_id_ref = flows.stamp(stale_id_ref)
    _refused(
        f_unequal.row("LR-039", stale_id_ref["record_id"], stale_id_ref, actor=actors.reviewer, when=at(108)),
        schemas,
        "W9 citation status supersedes_status_ref must name the root's current citation status",
        pin=ctx_b["pin"],
    )

    # F3: forged family_name not in the cited observation (adopted or unadopted) refuses at LR-039.
    for bad_entry in (
        {
            "observation_ref": flows.record_ref(ctx_b["obs_res"]),
            "family_name": "forged_unknown",
            "status": "unadopted",
            "adoption_ref": None,
        },
        {
            "observation_ref": flows.record_ref(obs_mem),
            "family_name": "headline",
            "status": "unadopted",
            "adoption_ref": None,
        },
        {
            "observation_ref": flows.record_ref(ctx_b["obs_res"]),
            "family_name": "whole_file",
            "status": "unadopted",
            "adoption_ref": None,
        },
        {
            "observation_ref": flows.record_ref(ctx_b["obs_res"]),
            "family_name": "other",
            "status": "adopted",
            "adoption_ref": flows.record_ref(ctx_b["adoption"]),
        },
    ):
        forged_fam = flows.citation_status_record(
            f_unequal.project_id,
            actors.reviewer,
            at(108),
            ctx_b["paper_root"],
            [bad_entry],
            supersedes_status=unequal,
        )
        _refused(
            f_unequal.row("LR-039", forged_fam["record_id"], forged_fam, actor=actors.reviewer, when=at(108)),
            schemas,
            "W9 citation status family does not belong to the cited observation",
            pin=ctx_b["pin"],
        )

    # Supersession chain errors: null supersedes when prior status exists, or pointing to stale status.
    no_sup = flows.citation_status_record(
        forger.project_id,
        actors.reviewer,
        at(108),
        root,
        [
            {
                "observation_ref": flows.record_ref(obs_res),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(adp),
            }
        ],
        supersedes_status=None,
    )
    _refused(
        forger.row("LR-039", no_sup["record_id"], no_sup, actor=actors.reviewer, when=at(108)),
        schemas,
        "W9 citation status supersedes_status_ref must name the root's current citation status",
        pin=pin,
    )

    # First status on a fresh root with non-null supersedes_status_ref refuses.
    forger_no_cit = flows.pilot_outcome_passed(Forger(events), actors, start=5)
    forger_no_cit, r_fresh = flows.paper_root_created(forger_no_cit, actors, start=10, paper_key="P01-B")
    bad_first_sup = flows.citation_status_record(
        forger_no_cit.project_id,
        actors.reviewer,
        at(108),
        r_fresh,
        [
            {
                "observation_ref": flows.record_ref(obs_res),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(adp),
            }
        ],
        supersedes_status=first_status,
    )
    # Use full_path_prerequisites with P01-B up to mapping by removing last LR-039 transaction.
    prior_events = Forger(forger_b.events[:-1])
    bad_first = flows.citation_status_record(
        prior_events.project_id,
        actors.reviewer,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            }
        ],
        supersedes_status=first_status,
    )
    _refused(
        prior_events.row("LR-039", bad_first["record_id"], bad_first, actor=actors.reviewer, when=at(106)),
        schemas,
        "W9 citation status supersedes_status_ref must be null when root has no prior status",
        pin=ctx_b["pin"],
    )
    assert bad_first_sup["supersedes_status_ref"] is not None

    # Wrong derived ID refuses.
    wrong_id = flows.citation_status_record(
        prior_events.project_id,
        actors.reviewer,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            }
        ],
        record_id=new_id("scope_definition"),
    )
    _refused(
        prior_events.row("LR-039", wrong_id["record_id"], wrong_id, actor=actors.reviewer, when=at(106)),
        schemas,
        "W9 citation status record_id is not derived from its subject",
        pin=ctx_b["pin"],
    )

    # Submitter == root creator refused; reviewer_actor_id != actor_id refused.
    by_creator = flows.citation_status_record(
        prior_events.project_id,
        actors.analyst,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            }
        ],
    )
    _refused(
        prior_events.row("LR-039", by_creator["record_id"], by_creator, actor=actors.analyst, when=at(106)),
        schemas,
        "W9 citation status submitter or reviewer is the paper root's creator",
        pin=ctx_b["pin"],
    )
    bad_actor = flows.citation_status_record(
        prior_events.project_id,
        actors.reviewer,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            }
        ],
    )
    bad_actor["derivation"]["reviewer_actor_id"] = actors.observer
    bad_actor = flows.stamp(bad_actor)
    _refused(
        prior_events.row("LR-039", bad_actor["record_id"], bad_actor, actor=actors.reviewer, when=at(106)),
        schemas,
        "W9 citation status reviewer_actor_id is not the event's actor",
        pin=ctx_b["pin"],
    )

    # Duplicate (obs, family) pair & tampered cited_family_set_sha256 refused.
    dup_pair = flows.citation_status_record(
        prior_events.project_id,
        actors.reviewer,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            },
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            },
        ],
    )
    _refused(
        prior_events.row("LR-039", dup_pair["record_id"], dup_pair, actor=actors.reviewer, when=at(106)),
        schemas,
        r"W9 citation status repeats an \(observation, family\) pair",
        pin=ctx_b["pin"],
    )

    bad_set_hash = deepcopy(unequal)
    bad_set_hash["cited_family_set_sha256"] = "f" * 64
    flows.stamp(bad_set_hash)
    _refused(
        forger_b.row("LR-039", bad_set_hash["record_id"], bad_set_hash, actor=actors.reviewer, when=at(107)),
        schemas,
        "W9 citation status cited_family_set_sha256 differs from families",
        pin=ctx_b["pin"],
    )

    # Wrong paper adoption & active adoption marked unadopted refused.
    adp_other_paper = flows.adoption(
        prior_events.project_id,
        actors.analyst,
        at(61),
        ctx_b["obs_res"],
        subject={"subject_kind": "families", "family_names": ["headline"]},
        intended_use={"description": "w9-use:manuscript-claims/P01-A", "successor_ref": None},
    )
    with_other_adp = flows.adoption_recorded(
        prior_events, actors, adp_other_paper, applicable_fixtures=("F-019", "S-017"), start=61
    )
    wrong_adp_status = flows.citation_status_record(
        with_other_adp.project_id,
        actors.reviewer,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(adp_other_paper),
            }
        ],
    )
    _refused(
        with_other_adp.row(
            "LR-039", wrong_adp_status["record_id"], wrong_adp_status, actor=actors.reviewer, when=at(106)
        ),
        schemas,
        "W9 citation status adoption does not cover the cited observation, family, or paper",
        pin=ctx_b["pin"],
    )

    unadopted_when_active = flows.citation_status_record(
        prior_events.project_id,
        actors.reviewer,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "unadopted",
                "adoption_ref": None,
            }
        ],
    )
    _refused(
        prior_events.row(
            "LR-039", unadopted_when_active["record_id"], unadopted_when_active, actor=actors.reviewer, when=at(106)
        ),
        schemas,
        "W9 citation status marks an actively adopted family as unadopted",
        pin=ctx_b["pin"],
    )

    # Suspended adoption refused at LR-039 (re-observe ctx_b["obs_res"] source with a new blob).
    reobs = flows.observation(
        prior_events.project_id,
        actors.observer,
        at(102),
        ctx_b["reg_res"],
        ctx_b["pin"],
        count=1,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(ctx_b["table"]),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", ctx_b["pin"])],
        source=flows.tracked("results/x.json", sha256="d" * 64, size=10, blob=flows.SHA1),
    )
    susp_forger = prior_events.row("LR-015", reobs["record_id"], reobs, actor=actors.observer, when=at(102))
    susp_status = flows.citation_status_record(
        susp_forger.project_id,
        actors.reviewer,
        at(106),
        ctx_b["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx_b["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_b["adoption"]),
            }
        ],
    )
    _refused(
        susp_forger.row("LR-039", susp_status["record_id"], susp_status, actor=actors.reviewer, when=at(106)),
        schemas,
        "W9 citation status cites a suspended adoption",
        pin=ctx_b["pin"],
    )


# --- LR-040 to LR-049: inventory & mapping checks, fixtures L, analyst rule M-3 -------------------------------


def test_lr040_to_lr049_checks_fixtures_and_analyst_rule(base, actors: Actors) -> None:
    events, schemas = base
    forger = flows.pilot_outcome_passed(Forger(events), actors, start=5)
    pin = flows.signature()
    forger, reg_root = flows.registered(
        forger, actors, path="papers/P01-A-JRSSA/", role="legacy_manuscript_root", start=10
    )
    forger, reg_nonroot = flows.registered(forger, actors, path="docs/note.md", role="legacy_coordination", start=15)
    obs_member = flows.observation(
        forger.project_id,
        actors.observer,
        at(20),
        reg_root,
        pin,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("papers/P01-A-JRSSA/drafts/a.tex"),
    )
    obs_unaccepted = flows.observation(
        forger.project_id,
        actors.observer,
        at(21),
        reg_root,
        pin,
        count=1,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("papers/P01-A-JRSSA/drafts/b.tex"),
    )
    forger = forger.row("LR-015", obs_member["record_id"], obs_member, actor=actors.observer, when=at(20))
    forger = forger.row("LR-015", obs_unaccepted["record_id"], obs_unaccepted, actor=actors.observer, when=at(21))
    batch = flows.acceptance(forger.project_id, actors.analyst, at(25), [obs_member])
    forger = flows.acceptance_recorded(forger, actors, batch, [], start=25)
    forger, root_a = flows.paper_root_created(forger, actors, start=35, paper_key="P01-A")
    forger, root_b = flows.paper_root_created(forger, actors, start=36, paper_key="P01-B")

    member_path = "papers/P01-A-JRSSA/drafts/a.tex"
    blob_a = obs_member["source_identity"]["git_blob"]

    # Non-root registration refused.
    bad_reg = flows.source_inventory_record(
        forger.project_id, actors.observer, at(40), reg_nonroot, [(member_path, blob_a, obs_member)]
    )
    _refused(
        flows.source_inventory_recorded(forger, actors, bad_reg, start=40, stop_after="LR-040"),
        schemas,
        "W9 source inventory registration must have role legacy_manuscript_root",
        pin=pin,
    )

    # Row ordinals gap refused.
    gap_inv = flows.source_inventory_record(
        forger.project_id, actors.observer, at(40), reg_root, [(member_path, blob_a, obs_member)]
    )
    gap_inv["rows"][0]["row_ordinal"] = 2
    flows.stamp(gap_inv)
    _refused(
        flows.source_inventory_recorded(forger, actors, gap_inv, start=40, stop_after="LR-040"),
        schemas,
        "W9 source inventory row ordinals do not run 1 to n",
        pin=pin,
    )

    # Row path not strictly under root refused.
    outside_inv = flows.source_inventory_record(
        forger.project_id, actors.observer, at(40), reg_root, [("results/outside.json", blob_a, obs_member)]
    )
    _refused(
        flows.source_inventory_recorded(forger, actors, outside_inv, start=40, stop_after="LR-040"),
        schemas,
        "W9 source inventory row path is not strictly under its root",
        pin=pin,
    )

    # Unaccepted observation refused.
    unacc_inv = flows.source_inventory_record(
        forger.project_id,
        actors.observer,
        at(40),
        reg_root,
        [("papers/P01-A-JRSSA/drafts/b.tex", obs_unaccepted["source_identity"]["git_blob"], obs_unaccepted)],
    )
    _refused(
        flows.source_inventory_recorded(forger, actors, unacc_inv, start=40, stop_after="LR-040"),
        schemas,
        "W9 source inventory row observation is not in a closed-reference acceptance",
        pin=pin,
    )

    # Wrong blob refused.
    wrong_blob_inv = flows.source_inventory_record(
        forger.project_id, actors.observer, at(40), reg_root, [(member_path, "f" * 40, obs_member)]
    )
    _refused(
        flows.source_inventory_recorded(forger, actors, wrong_blob_inv, start=40, stop_after="LR-040"),
        schemas,
        "W9 source inventory row differs from its observation's path or blob",
        pin=pin,
    )

    # M-3: observer may NOT request review on own inventory.
    good_inv = flows.source_inventory_record(
        forger.project_id, actors.observer, at(40), reg_root, [(member_path, blob_a, obs_member)]
    )
    _refused(
        flows.source_inventory_recorded(
            forger, actors, good_inv, start=40, tweaks={"LR-041": Tweak(actor=actors.observer)}, stop_after="LR-041"
        ),
        schemas,
        "W9 analyst is the proposal's creator",
        pin=pin,
    )

    # Owner point L: missing unconditional fixture on LR-041 / LR-043 / mismatch refuses.
    _refused(
        flows.source_inventory_recorded(
            forger, actors, good_inv, start=40, fixtures=("F-018", "F-023"), stop_after="LR-041"
        ),
        schemas,
        "W9 review request lacks required fixture F-037",
        pin=pin,
    )

    # Valid inventory recorded, then test LR-045..LR-049 mapping rules.
    with_inv = flows.source_inventory_recorded(forger, actors, good_inv, start=40)
    # Cross-paper M-10 at mapping: P01-A inventory mapped to P01-B root refuses.
    bad_map_root = flows.transition_mapping_record(with_inv.project_id, actors.analyst, at(50), good_inv, root_b, (1,))
    _refused(
        flows.transition_mapping_recorded(with_inv, actors, bad_map_root, start=50, stop_after="LR-045"),
        schemas,
        "W9 mapping target paper root path differs from inventory root registration path",
        pin=pin,
    )
    # Out-of-range ordinals refuse.
    bad_ord_map = flows.transition_mapping_record(with_inv.project_id, actors.analyst, at(50), good_inv, root_a, (1, 2))
    _refused(
        flows.transition_mapping_recorded(with_inv, actors, bad_ord_map, start=50, stop_after="LR-045"),
        schemas,
        "W9 mapping mapped_row_ordinals must be a unique non-empty subset of inventory rows",
        pin=pin,
    )
    # Valid mapping + analyst requesting LR-046 on their own LR-045 proposal passes (M-3)!
    good_map = flows.transition_mapping_record(with_inv.project_id, actors.analyst, at(50), good_inv, root_a, (1,))
    mapped = flows.transition_mapping_recorded(with_inv, actors, good_map, start=50)
    state = _replay(mapped, schemas, pin=pin)
    assert good_map["record_id"] in state["records"][reducers.TRANSITION_MAPPING]


# --- LR-050 to LR-055, W9-T5, W9-T17, departure 4 (§3.1 item 4) & Owner Point L ------------------------------------


def _supersede_record(
    forger: Forger, actors: Actors, target: dict[str, Any], replacement: dict[str, Any], start: float
) -> Forger:
    did = new_id("decision")
    rec = flows.stamp(
        {
            "schema_id": "ars://legacy/legacy-record-supersession",
            "schema_version": "1.0.0",
            "record_id": new_id("scope_definition"),
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": forger.project_id,
            "created_at": at(start),
            "created_by_actor_id": actors.analyst,
            "content_hash": "0" * 64,
            "superseded_ref": flows.record_ref(target),
            "replacing_ref": flows.record_ref(replacement),
            "reason": "test supersession",
            "reviewer_ref": pre_assigned_ref("review", new_id("review"), "x"),
            "decision_ref": pre_assigned_ref("decision", did, "x"),
        }
    )
    forger = forger.row("LR-056", rec["record_id"], rec, actor=actors.analyst, when=at(start))
    prop = {"new_decision_id": did, "governing_evidence_refs": ["W9:LR-059", rec["record_id"]]}
    forger = forger.row("LR-059", did, prop, actor=actors.analyst, when=at(start + 1))
    res = {"decision_id": did, "governing_evidence_refs": ["W9:LR-060"]}
    return forger.append(
        "ResolveW9AuthorityDecision",
        [("DecisionResolved", did, res), ("LegacyRecordSupersessionRecorded", rec["record_id"], deepcopy(rec))],
        actor=actors.owner,
        when=at(start + 2),
    )


def test_lr050_to_lr055_w9t5_w9t17_ruling3_and_owner_point_l(base, actors: Actors) -> None:
    events, schemas = base
    forger, ctx = flows.full_path_prerequisites(events, actors=actors)
    pin = ctx["pin"]

    # W9-T5: successor_owned -> legacy_owned fails schema; legacy_owned -> closed_reference refused at LR-050.
    rev_dir = flows.ownership_record(
        forger.project_id,
        actors.analyst,
        at(120),
        ctx["reg_root"],
        from_mode="successor_owned",
        to_mode="legacy_owned",
        mapping=None,
        paper_root=None,
    )
    _refused(
        forger.row("LR-050", rev_dir["record_id"], rev_dir, actor=actors.analyst, when=at(120)),
        schemas,
        "W9 event payload does not validate against its record schema",
        pin=pin,
    )

    bad_closed = flows.ownership_record(
        forger.project_id,
        actors.analyst,
        at(120),
        ctx["reg_root"],
        from_mode="legacy_owned",
        to_mode="closed_reference",
        mapping=None,
        paper_root=None,
    )
    _refused(
        forger.row("LR-050", bad_closed["record_id"], bad_closed, actor=actors.analyst, when=at(120)),
        schemas,
        "W9 LR-050 refuses legacy_owned to closed_reference",
        pin=pin,
    )

    # Direct _apply_ownership and _check_ownership_resolution unit checks for wrong row direction (LR-055).
    to_succ = flows.ownership_record(
        forger.project_id,
        actors.analyst,
        at(120),
        ctx["reg_root"],
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=ctx["mapping"],
        paper_root=ctx["paper_root"],
    )
    st_pre = _replay(forger, schemas, pin=pin)
    with pytest.raises(IntegrityError, match="W9 ownership transition differs from accepted LR-055"):
        reducers._apply_ownership(st_pre, "LR-055", to_succ)
    with pytest.raises(IntegrityError, match="W9 ownership transition differs from accepted LR-055"):
        reducers._check_ownership_resolution(st_pre, "LR-055", to_succ)

    # WP9.4-2 record §3.1 item 4: LR-053 for LR-054 requires w9-open-items-blob; LR-053 for LR-055 refuses it.
    _refused(
        flows.ownership_recorded(forger, actors, to_succ, start=120, open_items_blob=None),
        schemas,
        "W9 LR-054 Decision must carry one valid w9-open-items-blob entry",
        pin=pin,
    )
    ok_succ = flows.ownership_recorded(forger, actors, to_succ, start=120)
    to_closed = flows.ownership_record(
        ok_succ.project_id,
        actors.analyst,
        at(130),
        ctx["reg_root"],
        from_mode="successor_owned",
        to_mode="closed_reference",
        mapping=None,
        paper_root=None,
    )
    bad_55_refs = [
        "W9:LR-053",
        f"w9-subject:{to_closed['record_id']}",
        f"w9-subject-sha256:{to_closed['content_hash']}",
        f"w9-fixture:F-006:{new_id('review')}",
        f"w9-fixture:F-019:{new_id('review')}",
        f"w9-fixture:F-037:{new_id('review')}",
        f"w9-open-items-blob:{flows.OPEN_ITEMS_BLOB}",
    ]
    _refused(
        flows.ownership_recorded(
            ok_succ,
            actors,
            to_closed,
            start=130,
            tweaks={"LR-053": Tweak(payload={"governing_evidence_refs": bad_55_refs})},
            stop_after="LR-053",
        ),
        schemas,
        "W9 Decision fixture entry is malformed",
        pin=pin,
    )

    # T2: full positive LR-054 -> LR-055 replay asserts recorded reference_edges on all WP9.4-2 edge-writing rows.
    ok_closed = flows.ownership_recorded(ok_succ, actors, to_closed, start=130, open_items_blob=None)
    st_done = _replay(ok_closed, schemas, pin=pin)
    assert st_done["ownership"][ctx["reg_root"]["record_id"]] == "closed_reference"
    edges = st_done["reference_edges"]
    assert edges[ctx["paper_root"]["record_id"]] == []
    assert edges[ctx["inventory"]["record_id"]] == sorted(
        {
            ctx["reg_root"]["record_id"],
            ctx["obs_member"]["record_id"],
            ctx["inventory"]["reviewer_ref"]["id"],
            ctx["inventory"]["decision_ref"]["id"],
        }
    )
    assert edges[ctx["mapping"]["record_id"]] == sorted(
        {
            ctx["inventory"]["record_id"],
            ctx["paper_root"]["record_id"],
            ctx["mapping"]["reviewer_ref"]["id"],
            ctx["mapping"]["decision_ref"]["id"],
        }
    )
    assert edges[ctx["citation_status"]["record_id"]] == sorted(
        {
            ctx["paper_root"]["record_id"],
            ctx["obs_res"]["record_id"],
            ctx["adoption"]["record_id"],
        }
    )
    assert edges[to_succ["record_id"]] == sorted(
        {
            ctx["mapping"]["record_id"],
            ctx["reg_root"]["record_id"],
            ctx["paper_root"]["record_id"],
            to_succ["reviewer_ref"]["id"],
            to_succ["decision_ref"]["id"],
        }
    )
    assert edges[to_closed["record_id"]] == sorted(
        {
            ctx["reg_root"]["record_id"],
            to_closed["reviewer_ref"]["id"],
            to_closed["decision_ref"]["id"],
        }
    )

    # Unconditional fixture missing on LR-054 refuses; conditional F-038 admitted.
    _refused(
        flows.ownership_recorded(
            forger, actors, to_succ, start=120, fixtures=("F-006", "F-019", "F-023"), stop_after="LR-051"
        ),
        schemas,
        "W9 review request lacks required fixture F-037",
        pin=pin,
    )
    with_cond = flows.ownership_recorded(
        forger, actors, to_succ, start=120, fixtures=("F-006", "F-019", "F-023", "F-037", "F-038")
    )
    assert _replay(with_cond, schemas, pin=pin)["ownership"][ctx["reg_root"]["record_id"]] == "successor_owned"

    # Cross-paper M-10: non-root registration and P01-A mapping used to transition P01-B root registration both refuse.
    mismatched_map = flows.ownership_record(
        forger.project_id,
        actors.analyst,
        at(120),
        ctx["reg_res"],
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=ctx["mapping"],
        paper_root=ctx["paper_root"],
    )
    _refused(
        forger.row("LR-050", mismatched_map["record_id"], mismatched_map, actor=actors.analyst, when=at(120)),
        schemas,
        "W9 LR-054 subject registration must have role legacy_manuscript_root",
        pin=pin,
    )
    f_reg_b, reg_root_b = flows.registered(
        forger, actors, path="papers/P01-B-JRSSB/", role="legacy_manuscript_root", start=111
    )
    mismatched_paper = flows.ownership_record(
        f_reg_b.project_id,
        actors.analyst,
        at(120),
        reg_root_b,
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=ctx["mapping"],
        paper_root=ctx["paper_root"],
    )
    _refused(
        f_reg_b.row("LR-050", mismatched_paper["record_id"], mismatched_paper, actor=actors.analyst, when=at(120)),
        schemas,
        "W9 ownership subject registration does not match mapping inventory root",
        pin=pin,
    )
    f_root_b, root_b_for_m10 = flows.paper_root_created(forger, actors, start=111, paper_key="P01-B")
    mismatched_root_ref = flows.ownership_record(
        f_root_b.project_id,
        actors.analyst,
        at(120),
        ctx["reg_root"],
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=ctx["mapping"],
        paper_root=root_b_for_m10,
    )
    _refused(
        f_root_b.row(
            "LR-050", mismatched_root_ref["record_id"], mismatched_root_ref, actor=actors.analyst, when=at(120)
        ),
        schemas,
        "W9 mapping target paper root differs from ownership paper_root_ref",
        pin=pin,
    )

    # Unequal derivation hashes in citation status accepted at LR-039, refused at LR-054.
    unequal_status = flows.citation_status_record(
        forger.project_id,
        actors.reviewer,
        at(107),
        ctx["paper_root"],
        [
            {
                "observation_ref": flows.record_ref(ctx["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx["adoption"]),
            }
        ],
        extractor_output_sha256="b" * 64,
        reviewer_derivation_sha256="c" * 64,
        supersedes_status=ctx["citation_status"],
    )
    f_unequal = forger.row("LR-039", unequal_status["record_id"], unequal_status, actor=actors.reviewer, when=at(107))
    _refused(
        flows.ownership_recorded(f_unequal, actors, to_succ, start=120),
        schemas,
        "W9 LR-054 citation status extractor and reviewer derivations differ",
        pin=pin,
    )

    # Cited adoption active at LR-039 but suspended before LR-054 refuses at LR-054.
    reobs_after_39 = flows.observation(
        forger.project_id,
        actors.observer,
        at(115),
        ctx["reg_res"],
        pin,
        count=1,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(ctx["table"]),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", pin)],
        source=flows.tracked("results/x.json", sha256="d" * 64, size=10, blob=flows.SHA1),
    )
    f_susp_after_39 = forger.row(
        "LR-015", reobs_after_39["record_id"], reobs_after_39, actor=actors.observer, when=at(115)
    )
    _refused(
        flows.ownership_recorded(f_susp_after_39, actors, to_succ, start=120),
        schemas,
        "W9 LR-054 citation status cites a suspended adoption",
        pin=pin,
    )

    # M-9: status reviewer equal to inventory observer, ownership creator, or mapping analyst refused at LR-054.
    f_obs_rev, ctx_obs_rev = flows.full_path_prerequisites(
        events, actors=actors, citation_status_reviewer=actors.observer
    )
    tr_obs_rev = flows.ownership_record(
        f_obs_rev.project_id,
        actors.analyst,
        at(120),
        ctx_obs_rev["reg_root"],
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=ctx_obs_rev["mapping"],
        paper_root=ctx_obs_rev["paper_root"],
    )
    _refused(
        flows.ownership_recorded(f_obs_rev, actors, tr_obs_rev, start=120),
        schemas,
        "W9 citation status reviewer is not independent of the transition's producers",
        pin=ctx_obs_rev["pin"],
    )
    # Ownership creator == citation status reviewer (actors.reviewer).
    tr_rev_creator = flows.ownership_record(
        forger.project_id,
        actors.reviewer,
        at(120),
        ctx["reg_root"],
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=ctx["mapping"],
        paper_root=ctx["paper_root"],
    )
    alt_reviewer = new_id("actor")
    _refused(
        flows.ownership_recorded(
            forger,
            actors,
            tr_rev_creator,
            start=120,
            tweaks={
                "LR-050": Tweak(actor=actors.reviewer),
                "LR-051": Tweak(payload={"reviewer_capability": [alt_reviewer]}),
            },
        ),
        schemas,
        "W9 citation status reviewer is not independent of the transition's producers",
        pin=pin,
    )
    # Mapping analyst == citation status reviewer (root created by actors.author so LR-039 passes).
    f_map_rev, ctx_map_rev = flows.full_path_prerequisites(events, actors=actors, include_root_creation=False)
    f_map_rev, root_auth = flows.paper_root_created(f_map_rev, actors, start=75, paper_key="P01-A", actor=actors.author)
    map_by_analyst = flows.transition_mapping_record(
        f_map_rev.project_id, actors.analyst, at(95), ctx_map_rev["inventory"], root_auth, (1,)
    )
    f_map_rev = flows.transition_mapping_recorded(f_map_rev, actors, map_by_analyst, start=95)
    st_by_analyst = flows.citation_status_record(
        f_map_rev.project_id,
        actors.analyst,
        at(105),
        root_auth,
        [
            {
                "observation_ref": flows.record_ref(ctx_map_rev["obs_res"]),
                "family_name": "headline",
                "status": "adopted",
                "adoption_ref": flows.record_ref(ctx_map_rev["adoption"]),
            }
        ],
    )
    f_map_rev = f_map_rev.row("LR-039", st_by_analyst["record_id"], st_by_analyst, actor=actors.analyst, when=at(105))
    tr_map_rev = flows.ownership_record(
        f_map_rev.project_id,
        actors.owner,
        at(120),
        ctx_map_rev["reg_root"],
        from_mode="legacy_owned",
        to_mode="successor_owned",
        mapping=map_by_analyst,
        paper_root=root_auth,
    )
    _refused(
        flows.ownership_recorded(
            f_map_rev, actors, tr_map_rev, start=120, tweaks={"LR-050": Tweak(actor=actors.owner)}
        ),
        schemas,
        "W9 citation status reviewer is not independent of the transition's producers",
        pin=ctx_map_rev["pin"],
    )

    # R-m3: superseded mapping or superseded inventory refused at LR-050 / LR-054 (under ALL_ROWS where LR-056..060 run).
    sup_map = _supersede_record(forger, actors, ctx["mapping"], ctx["inventory"], start=112)
    sup_map_run = flows.ownership_recorded(sup_map, actors, to_succ, start=120)
    with pytest.raises(IntegrityError, match="W9 ownership transition names a superseded mapping"):
        replay_legacy(
            sup_map_run.events,
            schemas=schemas,
            routed_rows=ALL_ROWS,
            pinned_signatures=(pin,),
        )

    sup_inv = _supersede_record(forger, actors, ctx["inventory"], ctx["mapping"], start=112)
    sup_inv_run = flows.ownership_recorded(sup_inv, actors, to_succ, start=120)
    with pytest.raises(IntegrityError, match="W9 ownership transition mapping names a superseded inventory"):
        replay_legacy(
            sup_inv_run.events,
            schemas=schemas,
            routed_rows=ALL_ROWS,
            pinned_signatures=(pin,),
        )

    # Missing LR-022 at LR-054 when tested directly against _check_ownership_resolution.
    st_no_pilot = _replay(forger, schemas, pin=pin)
    st_no_pilot["decisions"] = {k: v for k, v in st_no_pilot["decisions"].items() if v.get("resolve_row") != "LR-022"}
    with pytest.raises(
        IntegrityError, match=r"W9 LR-054 requires a passed integration-pilot outcome Decision \(LR-022\)"
    ):
        reducers._check_ownership_resolution(st_no_pilot, "LR-054", to_succ)

    # WP9.3 Decision proposal with a 4th ref still refused (owner point L).
    f_reg = flows.registration(Forger(events).project_id, actors.analyst, at(0))
    f_prop = Forger(events).row("LR-003", f_reg["record_id"], f_reg, actor=actors.analyst, when=at(0))
    did_4 = f_reg["registration_decision_ref"]["id"]
    p4 = {
        **flows.decision_proposal("LR-004", f_reg, did_4, at(1)),
        "governing_evidence_refs": [
            "W9:LR-004",
            f"w9-subject:{f_reg['record_id']}",
            f"w9-subject-sha256:{f_reg['content_hash']}",
            f"w9-fixture:F-018:{new_id('review')}",
        ],
    }
    _refused(
        f_prop.row("LR-004", did_4, p4, actor=actors.analyst, when=at(1)),
        schemas,
        "W9 Decision proposal does not encode its subject",
    )


# --- W9-T21: reference graph cycles ----------------------------------------------------------------------------------


def test_w9_t21_graph_cycles_among_root_inventory_mapping_status_and_transition() -> None:
    state = reducers.new_legacy_state()
    reducers._add_edges(state, "obj_root", ["obj_other"])
    reducers._add_edges(state, "obj_inv", ["obj_root"])
    reducers._add_edges(state, "obj_map", ["obj_inv", "obj_root"])
    reducers._add_edges(state, "obj_status", ["obj_root"])
    reducers._add_edges(state, "obj_trans", ["obj_map", "obj_root"])
    with pytest.raises(IntegrityError, match="W9 reference cycle among roots, mappings, transitions and Decisions"):
        reducers._add_edges(state, "obj_other", ["obj_trans"])
    with pytest.raises(IntegrityError, match="W9 record references itself"):
        reducers._add_edges(state, "obj_self", ["obj_self"])


# --- Owner point K (readings 1-4), non-root control & P-087 item 6 ---------------------------------------------------


def test_owner_point_k_readings_1_to_4_and_non_root_controls(base, actors: Actors) -> None:
    events, schemas = base
    forger = Forger(events)
    pin = flows.signature()
    forger, reg_root = flows.registered(
        forger, actors, path="papers/P01-A-JRSSA/", role="legacy_manuscript_root", start=10
    )

    # F1: LR-011 must refuse a legacy_manuscript_root registration before checking the source.
    root_light_inv = flows.inventory(
        forger.project_id,
        actors.observer,
        at(14),
        reg_root,
        segment(b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n", "tracker_task_row"),
        source=flows.tracked("papers/P01-A-JRSSA/drafts/main.tex"),
    )
    _refused(
        forger.row("LR-011", root_light_inv["record_id"], root_light_inv, actor=actors.observer, when=at(14)),
        schemas,
        "W9 light inventory cannot target a legacy_manuscript_root registration",
        pin=pin,
    )

    # K1: root directory itself (with or without trailing '/') or path outside root refused at LR-015.
    for bad_path in ("papers/P01-A-JRSSA/", "papers/P01-A-JRSSA", "papers/P01-A-JRSSA-old/x.tex"):
        bad_obs = flows.observation(
            forger.project_id,
            actors.observer,
            at(15),
            reg_root,
            pin,
            selector={"selector_kind": "whole_file"},
            families=[flows.signed_family("whole_file", pin)],
            source=flows.tracked(bad_path),
        )
        _refused(
            forger.row("LR-015", bad_obs["record_id"], bad_obs, actor=actors.observer, when=at(15)),
            schemas,
            "W9 source does not match its registration's kind, root and path",
            pin=pin,
        )

    # K2, K3, K4: two members with identical Git blob (e.g. .gitkeep files) + a.npy & b.npy observed under root.
    shared_blob = "a" * 40
    obs_gk1 = flows.observation(
        forger.project_id,
        actors.observer,
        at(20),
        reg_root,
        pin,
        count=0,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("papers/P01-A-JRSSA/drafts/.gitkeep", sha256="1" * 64, blob=shared_blob),
    )
    obs_gk2 = flows.observation(
        forger.project_id,
        actors.observer,
        at(21),
        reg_root,
        pin,
        count=1,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("papers/P01-A-JRSSA/figures/.gitkeep", sha256="1" * 64, blob=shared_blob),
    )
    obs_a = flows.observation(
        forger.project_id,
        actors.observer,
        at(22),
        reg_root,
        pin,
        count=2,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("papers/P01-A-JRSSA/data/a.npy", sha256="2" * 64, blob="2" * 40),
    )
    forger = forger.row("LR-015", obs_gk1["record_id"], obs_gk1, actor=actors.observer, when=at(20))
    forger = forger.row("LR-015", obs_gk2["record_id"], obs_gk2, actor=actors.observer, when=at(21))
    forger = forger.row("LR-015", obs_a["record_id"], obs_a, actor=actors.observer, when=at(22))
    batch = flows.acceptance(forger.project_id, actors.analyst, at(30), [obs_gk1, obs_gk2, obs_a])
    forger = flows.acceptance_recorded(forger, actors, batch, [], start=30)

    adp_a = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(45),
        obs_a,
        subject={"subject_kind": "whole_file", "rehash_at_use": True},
        intended_use={"description": "w9-use:manuscript-claims/P01-A", "successor_ref": None},
    )
    forger = flows.adoption_recorded(forger, actors, adp_a, applicable_fixtures=("F-019", "S-017"), start=45)

    # K3: observing unchanged member b.npy leaves adoption of a.npy ACTIVE and marks nothing stale.
    obs_b = flows.observation(
        forger.project_id,
        actors.observer,
        at(55),
        reg_root,
        pin,
        count=3,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("papers/P01-A-JRSSA/data/b.npy", sha256="3" * 64, blob="3" * 40),
    )
    forger = forger.row("LR-015", obs_b["record_id"], obs_b, actor=actors.observer, when=at(55))
    state = _replay(forger, schemas, pin=pin)
    assert reg_root["record_id"] not in state["ownership"]
    assert state["records"].get(reducers.OWNERSHIP, {}) == {}
    assert state["stale_observations"] == []
    assert projection_read.adoption_status(state, adp_a["record_id"]) == {
        "adoption_id": adp_a["record_id"],
        "status": "active",
        "cause": None,
    }

    # F2 (K reading 3): family adoption on root/a.json stays ACTIVE when root/b.json shares family 'headline';
    # observing root/a.json again with 'headline' suspends it; non-root family adoption suspends across export paths.
    fa_path = "papers/P01-A-JRSSA/data/fa.json"
    fb_path = "papers/P01-A-JRSSA/data/fb.json"
    fa_sha, fb_sha = "4" * 64, "5" * 64
    fa_blob, fb_blob = "4" * 40, "5" * 40
    forger_f, reg_root_f = flows.registered(
        Forger(events), actors, path="papers/P01-A-JRSSA/", role="legacy_manuscript_root", start=10
    )
    forger_f, tbl_fa = flows.membership_recorded(forger_f, actors, path=fa_path, sha256=fa_sha, size=10, start=12)
    forger_f, tbl_fb = flows.membership_recorded(forger_f, actors, path=fb_path, sha256=fb_sha, size=10, start=18)
    obs_fa = flows.observation(
        forger_f.project_id,
        actors.observer,
        at(25),
        reg_root_f,
        pin,
        count=0,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(tbl_fa),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", pin)],
        source=flows.tracked(fa_path, sha256=fa_sha, size=10, blob=fa_blob),
    )
    forger_f = forger_f.row("LR-015", obs_fa["record_id"], obs_fa, actor=actors.observer, when=at(25))
    batch_fa = flows.acceptance(forger_f.project_id, actors.analyst, at(30), [obs_fa])
    forger_f = flows.acceptance_recorded(forger_f, actors, batch_fa, [], start=30)
    adp_fa = flows.adoption(
        forger_f.project_id,
        actors.analyst,
        at(45),
        obs_fa,
        subject={"subject_kind": "families", "family_names": ["headline"]},
        intended_use={"description": "w9-use:manuscript-claims/P01-A", "successor_ref": None},
    )
    forger_f = flows.adoption_recorded(forger_f, actors, adp_fa, applicable_fixtures=("F-019", "S-017"), start=45)
    obs_fb = flows.observation(
        forger_f.project_id,
        actors.observer,
        at(55),
        reg_root_f,
        pin,
        count=1,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(tbl_fb),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", pin)],
        source=flows.tracked(fb_path, sha256=fb_sha, size=10, blob=fb_blob),
    )
    forger_fb = forger_f.row("LR-015", obs_fb["record_id"], obs_fb, actor=actors.observer, when=at(55))
    st_fb = _replay(forger_fb, schemas, pin=pin)
    assert projection_read.adoption_status(st_fb, adp_fa["record_id"]) == {
        "adoption_id": adp_fa["record_id"],
        "status": "active",
        "cause": None,
    }
    obs_fa_2 = flows.observation(
        forger_fb.project_id,
        actors.observer,
        at(60),
        reg_root_f,
        pin,
        count=2,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(tbl_fa),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", pin)],
        source=flows.tracked(fa_path, sha256=fa_sha, size=10, blob=fa_blob),
    )
    forger_fa_2 = forger_fb.row("LR-015", obs_fa_2["record_id"], obs_fa_2, actor=actors.observer, when=at(60))
    st_fa_2 = _replay(forger_fa_2, schemas, pin=pin)
    assert projection_read.adoption_status(st_fa_2, adp_fa["record_id"]) == {
        "adoption_id": adp_fa["record_id"],
        "status": "suspended",
        "cause": "later_observation",
    }

    # Control (R4-m1): non-root legacy_decision_log_entry with two different export paths STILL marks earlier stale.
    forger_cl, reg_cl = flows.registered(
        Forger(events), actors, path="exports/cl-main.json", role="legacy_decision_log_entry", start=10, file_id="99"
    )
    exports = (
        {"retained_copy": {"repository_path": "exports/cl-1.json", "git_commit": flows.SHA1, "git_blob": "1" * 40}},
        {"retained_copy": {"repository_path": "exports/cl-2.json", "git_commit": flows.SHA1, "git_blob": "2" * 40}},
    )
    cl_1 = flows.observation(
        forger_cl.project_id,
        actors.observer,
        at(20),
        reg_cl,
        pin,
        count=0,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("exports/cl-1.json", sha256="1" * 64, blob="1" * 40),
    )
    cl_2 = flows.observation(
        forger_cl.project_id,
        actors.observer,
        at(25),
        reg_cl,
        pin,
        count=1,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("exports/cl-2.json", sha256="2" * 64, blob="2" * 40),
    )
    forger_cl = forger_cl.row("LR-015", cl_1["record_id"], cl_1, actor=actors.observer, when=at(20))
    forger_cl = forger_cl.row("LR-015", cl_2["record_id"], cl_2, actor=actors.observer, when=at(25))
    st_cl = _replay(forger_cl, schemas, pin=pin, accepted_cl_export=exports)
    assert st_cl["stale_observations"] == [cl_1["record_id"]]

    # Non-root family adoption control for F2: later json_family_set observation on another CL export path suspends it.
    cl_same_blob = "5" * 40
    cl_same_sha = "5" * 64
    exports_fam = (
        {
            "retained_copy": {
                "repository_path": "exports/cl-f1.json",
                "git_commit": flows.SHA1,
                "git_blob": cl_same_blob,
            }
        },
        {
            "retained_copy": {
                "repository_path": "exports/cl-f2.json",
                "git_commit": flows.SHA1,
                "git_blob": cl_same_blob,
            }
        },
    )
    forger_cl_f, reg_cl_f = flows.registered(
        Forger(events), actors, path="exports/cl-fam.json", role="legacy_decision_log_entry", start=10, file_id="98"
    )
    forger_cl_f, tbl_cl_1 = flows.membership_recorded(
        forger_cl_f, actors, path="exports/cl-f1.json", sha256=cl_same_sha, size=10, start=12
    )
    forger_cl_f, tbl_cl_2 = flows.membership_recorded(
        forger_cl_f, actors, path="exports/cl-f2.json", sha256=cl_same_sha, size=10, start=18
    )
    cl_fam_1 = flows.observation(
        forger_cl_f.project_id,
        actors.observer,
        at(25),
        reg_cl_f,
        pin,
        count=0,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(tbl_cl_1),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", pin)],
        source=flows.tracked("exports/cl-f1.json", sha256=cl_same_sha, size=10, blob=cl_same_blob),
    )
    forger_cl_f = forger_cl_f.row("LR-015", cl_fam_1["record_id"], cl_fam_1, actor=actors.observer, when=at(25))
    batch_cl = flows.acceptance(forger_cl_f.project_id, actors.analyst, at(30), [cl_fam_1])
    forger_cl_f = flows.acceptance_recorded(forger_cl_f, actors, batch_cl, [], start=30)
    adp_cl = flows.adoption(
        forger_cl_f.project_id,
        actors.analyst,
        at(45),
        cl_fam_1,
        subject={"subject_kind": "families", "family_names": ["headline"]},
        intended_use={"description": "w9-use:claim-evidence/c1", "successor_ref": None},
    )
    forger_cl_f = flows.adoption_recorded(forger_cl_f, actors, adp_cl, applicable_fixtures=("F-019", "S-017"), start=45)
    cl_fam_2 = flows.observation(
        forger_cl_f.project_id,
        actors.observer,
        at(55),
        reg_cl_f,
        pin,
        count=1,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(tbl_cl_2),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", pin)],
        source=flows.tracked("exports/cl-f2.json", sha256=cl_same_sha, size=10, blob=cl_same_blob),
    )
    forger_cl_f = forger_cl_f.row("LR-015", cl_fam_2["record_id"], cl_fam_2, actor=actors.observer, when=at(55))
    st_cl_f = _replay(forger_cl_f, schemas, pin=pin, accepted_cl_export=exports_fam)
    assert st_cl_f["stale_observations"] == []
    assert projection_read.adoption_status(st_cl_f, adp_cl["record_id"]) == {
        "adoption_id": adp_cl["record_id"],
        "status": "suspended",
        "cause": "later_observation",
    }


def test_p087_item6_second_registration_refused_with_active_whole_file_adoption(base, actors: Actors) -> None:
    events, schemas = base
    forger = Forger(events)
    pin = flows.signature()
    forger, reg_file = flows.registered(
        forger, actors, path="data/raw.npy", role="legacy_research_result", kind="git_tracked", file_id="401", start=5
    )
    forger, reg_root = flows.registered(
        forger, actors, path="papers/P01-A-JRSSA/", role="legacy_manuscript_root", start=10, file_id="402"
    )
    obs_file = flows.observation(
        forger.project_id,
        actors.observer,
        at(20),
        reg_file,
        pin,
        selector={"selector_kind": "whole_file"},
        families=[flows.signed_family("whole_file", pin)],
        source=flows.tracked("data/raw.npy", sha256="f" * 64, blob="f" * 40),
    )
    forger = forger.row("LR-015", obs_file["record_id"], obs_file, actor=actors.observer, when=at(20))
    batch = flows.acceptance(forger.project_id, actors.analyst, at(30), [obs_file])
    tr = flows.ownership_transition(batch, reg_file)
    forger = flows.acceptance_recorded(forger, actors, batch, [tr], start=30)
    adp_file = flows.adoption(
        forger.project_id,
        actors.analyst,
        at(45),
        obs_file,
        subject={"subject_kind": "whole_file", "rehash_at_use": True},
        intended_use={"description": "w9-use:manuscript-claims/P01-A", "successor_ref": None},
    )
    forger = flows.adoption_recorded(forger, actors, adp_file, applicable_fixtures=("F-019", "S-017"), start=45)

    for variant_kwargs in (
        {"path": "DATA/raw.npy", "file_id": "999", "target": "C:/scratch/DATA/raw.npy"},
        {"path": "data/alias.npy", "file_id": "401", "target": "C:/other/alias.npy"},
        # T1: isolate folded-path prefix collision vs physical canonical_target prefix collision.
        {"path": "papers/P01-A-JRSSA/drafts/a.npy", "file_id": "998", "target": "D:/outside/drafts/a.npy"},
        {"path": "external/aliased_a.npy", "file_id": "997", "target": "C:/scratch/papers/P01-A-JRSSA/drafts/a.npy"},
    ):
        dup = flows.registration(forger.project_id, actors.analyst, at(60), **variant_kwargs)
        _refused(
            forger.row("LR-003", dup["record_id"], dup, actor=actors.analyst, when=at(60)),
            schemas,
            "W9 registration of a path or physical identity already registered or proposed",
            pin=pin,
        )
    st_ok = _replay(forger, schemas, pin=pin)
    assert projection_read.adoption_status(st_ok, adp_file["record_id"])["status"] == "active"


# --- Owner point O, R6, R7 & P-087 items 3-4: prefix collisions, equality, projection prefix -----------------------


def test_owner_point_o_prefix_collisions_every_role_equality_and_projection_prefix(base, actors: Actors) -> None:
    events, schemas = base
    forger = Forger(events)
    root_path = "papers/P01-A-JRSSA/"
    root_target = "C:/checkout-a/papers/P01-A-JRSSA"

    # Non-git_tracked legacy_manuscript_root refused in replay (R6-m1).
    bad_kind = flows.registration(
        forger.project_id, actors.analyst, at(0), path=root_path, role="legacy_manuscript_root", kind="untracked_file"
    )
    _refused(
        forger.row("LR-003", bad_kind["record_id"], bad_kind, actor=actors.analyst, when=at(0)),
        schemas,
        "W9 legacy_manuscript_root registration must be git_tracked",
    )

    # Recorded root -> member under root refused (exact case, case variant, and across binding move new root_id).
    f_rec_root, _ = flows.registered(
        forger, actors, path=root_path, role="legacy_manuscript_root", target=root_target, file_id="501", start=0
    )
    # Open proposal root -> member under root refused too.
    prop_root = flows.registration(
        forger.project_id,
        actors.analyst,
        at(0),
        path=root_path,
        role="legacy_manuscript_root",
        target=root_target,
        file_id="501",
    )
    f_open_root = forger.row("LR-003", prop_root["record_id"], prop_root, actor=actors.analyst, when=at(0))
    for base_f in (f_rec_root, f_open_root):
        child = flows.registration(
            forger.project_id,
            actors.analyst,
            at(10),
            path="papers/P01-A-JRSSA/_project.md",
            role="legacy_coordination",
            target=f"{root_target}/_project.md",
            file_id="502",
        )
        _refused(
            base_f.row("LR-003", child["record_id"], child, actor=actors.analyst, when=at(10)),
            schemas,
            "W9 registration of a path or physical identity already registered or proposed",
        )
        # Case variant as untracked_file refused by folded path AND target prefix (R6-M1).
        case_child = flows.registration(
            forger.project_id,
            actors.analyst,
            at(10),
            path="papers/p01-a-jrssa/_project.md",
            role="legacy_coordination",
            kind="untracked_file",
            target="C:/CHECKOUT-A/papers/P01-A-JRSSA/_project.md",
            file_id="503",
        )
        _refused(
            base_f.row("LR-003", case_child["record_id"], case_child, actor=actors.analyst, when=at(10)),
            schemas,
            "W9 registration of a path or physical identity already registered or proposed",
        )
        # Across binding move with new root_id and different checkout target: folded path half refuses (R7-M1).
        moved_child = flows.registration(
            forger.project_id,
            actors.analyst,
            at(10),
            path="papers/P01-A-JRSSA/_project.md",
            role="legacy_coordination",
            root_id="repo-moved",
            target="C:/checkout-b/papers/P01-A-JRSSA/_project.md",
            file_id="504",
        )
        _refused(
            base_f.row("LR-003", moved_child["record_id"], moved_child, actor=actors.analyst, when=at(10)),
            schemas,
            "W9 registration of a path or physical identity already registered or proposed",
        )
        # Unrelated normalized_path sharing canonical_target prefix refuses via physical target check.
        target_only_child = flows.registration(
            forger.project_id,
            actors.analyst,
            at(10),
            path="aliases/p01a_project.md",
            role="legacy_coordination",
            target=f"{root_target}/_project.md",
            file_id="590",
        )
        _refused(
            base_f.row("LR-003", target_only_child["record_id"], target_only_child, actor=actors.analyst, when=at(10)),
            schemas,
            "W9 registration of a path or physical identity already registered or proposed",
        )

    # Reverse direction: member recorded (or open proposal) -> root over it refused; case variant reverse refused.
    f_rec_child, _ = flows.registered(
        forger,
        actors,
        path="papers/p01-a-jrssa/_project.md",
        role="legacy_coordination",
        kind="untracked_file",
        target=f"{root_target}/_project.md",
        file_id="505",
        start=0,
    )
    prop_child = flows.registration(
        forger.project_id,
        actors.analyst,
        at(0),
        path="papers/p01-a-jrssa/_project.md",
        role="legacy_coordination",
        kind="untracked_file",
        target=f"{root_target}/_project.md",
        file_id="505",
    )
    f_open_child = forger.row("LR-003", prop_child["record_id"], prop_child, actor=actors.analyst, when=at(0))
    for base_f in (f_rec_child, f_open_child):
        over_root = flows.registration(
            forger.project_id,
            actors.analyst,
            at(10),
            path=root_path,
            role="legacy_manuscript_root",
            target=root_target,
            file_id="506",
        )
        _refused(
            base_f.row("LR-003", over_root["record_id"], over_root, actor=actors.analyst, when=at(10)),
            schemas,
            "W9 registration of a path or physical identity already registered or proposed",
        )
    f_rec_target_child, _ = flows.registered(
        forger,
        actors,
        path="aliases/p01a_project.md",
        role="legacy_coordination",
        target=f"{root_target}/_project.md",
        file_id="591",
        start=0,
    )
    over_root_target = flows.registration(
        forger.project_id,
        actors.analyst,
        at(10),
        path=root_path,
        role="legacy_manuscript_root",
        target=root_target,
        file_id="592",
    )
    _refused(
        f_rec_target_child.row(
            "LR-003", over_root_target["record_id"], over_root_target, actor=actors.analyst, when=at(10)
        ),
        schemas,
        "W9 registration of a path or physical identity already registered or proposed",
    )

    # Controls on recorded root: component-boundary sibling & vault_root with same relative path ARE admitted.
    sibling = flows.registration(
        forger.project_id,
        actors.analyst,
        at(10),
        path="papers/P01-A-JRSSA-old/x.md",
        role="legacy_coordination",
        target="C:/checkout-a/papers/P01-A-JRSSA-old/x.md",
        file_id="507",
    )
    vault_same_rel = flows.registration(
        forger.project_id,
        actors.analyst,
        at(11),
        path="papers/P01-A-JRSSA/x.md",
        role="legacy_coordination",
        kind="vault_file",
        root_kind="vault_root",
        root_id="vault",
        target="C:/vault/papers/P01-A-JRSSA/x.md",
        file_id="508",
    )
    f_ctrl = f_rec_root.row("LR-003", sibling["record_id"], sibling, actor=actors.analyst, when=at(10))
    f_ctrl = f_ctrl.row("LR-003", vault_same_rel["record_id"], vault_same_rel, actor=actors.analyst, when=at(11))
    assert _replay(f_ctrl, schemas)["proposals"][sibling["record_id"]]["kind"] == "legacy_path_registration"

    # Every-role equality (R6-M2, R7-m1, P-087 item 4):
    f_base, _ = flows.registered(
        forger,
        actors,
        path="results/first.json",
        role="legacy_research_result",
        target="C:/a/first.json",
        file_id="777",
        start=0,
    )
    # Same (volume_serial_number, stable_file_id) at unrelated path & target refused.
    same_vol_id = flows.registration(
        forger.project_id,
        actors.analyst,
        at(10),
        path="results/unrelated.json",
        target="C:/completely/other.json",
        file_id="777",
    )
    _refused(
        f_base.row("LR-003", same_vol_id["record_id"], same_vol_id, actor=actors.analyst, when=at(10)),
        schemas,
        "W9 registration of a path or physical identity already registered or proposed",
    )
    # Same stable_file_id on another volume_serial_number admitted.
    other_vol = flows.registration(
        forger.project_id,
        actors.analyst,
        at(10),
        path="results/other_vol.json",
        target="D:/b/other.json",
        physical_identity=flows.physical_identity("D:/b/other.json", "777") | {"volume_serial_number": "2"},
    )
    # Wait: volume_serial_number is a top-level field of physical_identity.
    other_vol["physical_identity"]["volume_serial_number"] = "2"
    flows.stamp(other_vol)
    # Same path (case variant) or same path with different root_id (P-087 item 4) refused.
    case_path = flows.registration(
        forger.project_id, actors.analyst, at(10), path="Results/FIRST.JSON", target="C:/x/y.json", file_id="778"
    )
    _refused(
        f_base.row("LR-003", case_path["record_id"], case_path, actor=actors.analyst, when=at(10)),
        schemas,
        "W9 registration of a path or physical identity already registered or proposed",
    )
    diff_root_id = flows.registration(
        forger.project_id,
        actors.analyst,
        at(10),
        path="results/first.json",
        root_id="repo-2",
        target="C:/x/z.json",
        file_id="779",
    )
    _refused(
        f_base.row("LR-003", diff_root_id["record_id"], diff_root_id, actor=actors.analyst, when=at(10)),
        schemas,
        "W9 registration of a path or physical identity already registered or proposed",
    )
    f_distinct = f_base.row("LR-003", other_vol["record_id"], other_vol, actor=actors.analyst, when=at(10))
    assert _replay(f_distinct, schemas)["proposals"][other_vol["record_id"]]["kind"] == "legacy_path_registration"

    # R7-M2: projection prefix check is case-folded.
    bad_proj = flows.registration(
        forger.project_id,
        actors.analyst,
        at(0),
        path=".Research-System/Projections/Legacy/p.json",
        role="legacy_coordination",
    )
    _refused(
        forger.row("LR-003", bad_proj["record_id"], bad_proj, actor=actors.analyst, when=at(0)),
        schemas,
        "W9 legacy role under the legacy projection directory",
    )
    ok_proj = flows.registration(
        forger.project_id,
        actors.analyst,
        at(0),
        path=".research-system/projections/legacy/p.json",
        role="legacy_read_only_projection",
        kind="untracked_file",
        ownership_mode="successor_owned",
        writer_classes=["ars_projection_rebuild"],
    )
    assert (
        _replay(forger.row("LR-003", ok_proj["record_id"], ok_proj, actor=actors.analyst, when=at(0)), schemas)[
            "proposals"
        ][ok_proj["record_id"]]["kind"]
        == "legacy_path_registration"
    )
