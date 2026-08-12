from __future__ import annotations

from copy import deepcopy

import pytest

from research_system.discovery.authority import (
    AuthorityRejected,
    prepare_authority_transition,
    replay_authority,
    subject_sha256,
)


AUTHOR = "act_author"
OBSERVER = "act_observer"
REVIEWER = "act_reviewer"
REQUESTER = "act_requester"
PROPOSER = "act_decision_proposer"
OWNER = "act_stephen"


def _subject(kind: str) -> dict[str, object]:
    dossier_id = "obj_019fed25-b33e-7740-b280-000000000913"
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    if kind == "dossier_expected_set":
        subject = {
            "authority_kind": kind,
            "record_id": "expected:tda-scale:1.0.3",
            "record_revision": 3,
            "project_id": project_id,
            "scope_id": dossier_id,
            "owner_requirement_refs": ["req_wp66"],
            "content_sha256": "1" * 64,
            "expected_set": {
                "expected_set_id": "expected:tda-scale:1.0.3",
                "revision": 3,
                "project_id": project_id,
                "dossier_id": dossier_id,
                "content_hash": "1" * 64,
                "admission_profile_id": "profile:wp6.6:dossier-admission",
                "admission_profile_revision": 1,
            },
            "admission_profile_decision": {
                "profile_id": "profile:wp6.6:dossier-admission",
                "profile_revision": 1,
                "dispatchable": False,
                "provider_execution": "forbidden",
            },
        }
    else:
        subject = {
            "authority_kind": kind,
            "record_id": "path-registration:tda-scale",
            "record_revision": 1,
            "project_id": project_id,
            "scope_id": dossier_id,
            "owner_requirement_refs": ["req_wp66"],
            "content_sha256": "2" * 64,
            "collision_status": "no_collision",
            "registered_roots": [{"root_id": "repo", "path": "$REPOSITORY_CONTRACT_ROOT"}],
        }
    subject["subject_sha256"] = subject_sha256(subject)
    return subject


def _run(kind: str) -> tuple[dict[str, object], ...]:
    subject = _subject(kind)
    events: tuple[dict[str, object], ...] = _run("dossier_expected_set") if kind == "path_registration" else ()
    steps = (
        ("register", AUTHOR, {"subject": subject}),
        (
            "observe",
            OBSERVER,
            {
                "subject_sha256": subject["subject_sha256"],
                "repository_path": f"authority/{kind}.json",
                "git_commit": "2" * 40,
                "git_blob": "3" * 40,
                "file_size": 123,
                "file_sha256": "4" * 64,
            },
        ),
        ("request_review", REQUESTER, {"reviewer_actor_id": REVIEWER}),
        (
            "record_review",
            REVIEWER,
            {
                "verdict": "approve",
                "unchanged_subject_sha256": subject["subject_sha256"],
                "unchanged_file_sha256": "4" * 64,
                "reconstruction_sha256": "5" * 64,
            },
        ),
        ("propose", PROPOSER, {"decision_id": f"dec_{kind}", "proposed_decision": "accept"}),
        (
            "resolve",
            OWNER,
            {"decision_id": f"dec_{kind}", "decision": "accept", "transaction_id": f"txn_{kind}"},
        ),
    )
    for action, actor, payload in steps:
        events += prepare_authority_transition(events=events, kind=kind, action=action, actor_id=actor, payload=payload)
    return events


@pytest.mark.parametrize(
    ("kind", "row_ids", "event_types"),
    (
        (
            "dossier_expected_set",
            tuple(f"OR-{number}" for number in range(110, 116)),
            (
                "DossierExpectedSetContentRegistered",
                "W11AuthorityFileObserved",
                "ReviewRequested",
                "ReviewVerdictRecorded",
                "DecisionProposed",
                "DecisionResolved",
                "DossierExpectedSetAccepted",
            ),
        ),
        (
            "path_registration",
            tuple(f"OR-{number}" for number in range(116, 122)),
            (
                "PathRegistrationContentRegistered",
                "W11AuthorityFileObserved",
                "ReviewRequested",
                "ReviewVerdictRecorded",
                "DecisionProposed",
                "DecisionResolved",
                "PathRegistrationAccepted",
            ),
        ),
    ),
)
def test_authority_positive_path_is_ordered_w2_ready_and_replay_equivalent(
    kind: str, row_ids: tuple[str, ...], event_types: tuple[str, ...]
) -> None:
    events = _run(kind)
    state = replay_authority(events)
    kind_events = tuple(event for event in events if event["authority_kind"] == kind)

    assert tuple(event["event_type"] for event in kind_events) == event_types
    assert tuple(dict.fromkeys(event["owner_row_id"] for event in kind_events)) == row_ids
    assert state[kind]["status"] == "accepted"
    assert state[kind]["actors"] == {
        "author": AUTHOR,
        "observer": OBSERVER,
        "review_requester": REQUESTER,
        "reviewer": REVIEWER,
        "decision_proposer": PROPOSER,
        "owner": OWNER,
    }
    assert kind_events[2]["payload"]["schema_id"] == "ars://core/event/ReviewRequested"
    assert kind_events[3]["payload"]["schema_id"] == "ars://core/event/ReviewVerdictRecorded"
    assert kind_events[4]["payload"]["schema_id"] == "ars://core/event/DecisionProposed"
    assert kind_events[5]["payload"]["schema_id"] == "ars://core/event/DecisionResolved"
    assert kind_events[-1]["payload"]["transaction_id"] == f"txn_{kind}"


def test_authority_rejects_related_actors_tamper_stale_collision_and_second_acceptance() -> None:
    subject = _subject("path_registration")
    dossier_events = _run("dossier_expected_set")
    registered = dossier_events + prepare_authority_transition(
        events=dossier_events,
        kind="path_registration",
        action="register",
        actor_id=AUTHOR,
        payload={"subject": subject},
    )

    with pytest.raises(AuthorityRejected, match="actor_not_independent"):
        prepare_authority_transition(
            events=registered,
            kind="path_registration",
            action="observe",
            actor_id=AUTHOR,
            payload={
                "subject_sha256": subject["subject_sha256"],
                "repository_path": "x",
                "git_commit": "2" * 40,
                "git_blob": "3" * 40,
                "file_size": 1,
                "file_sha256": "4" * 64,
            },
        )

    events = _run("path_registration")
    tampered = list(deepcopy(events))
    observed_index = next(
        index
        for index, event in enumerate(tampered)
        if event["authority_kind"] == "path_registration" and event["event_type"] == "W11AuthorityFileObserved"
    )
    tampered[observed_index]["payload"]["file_sha256"] = "9" * 64
    with pytest.raises(AuthorityRejected, match="file_identity_mismatch"):
        replay_authority(tampered)

    review_tampered = list(deepcopy(events))
    review_index = next(
        index
        for index, event in enumerate(review_tampered)
        if event["authority_kind"] == "path_registration" and event["event_type"] == "ReviewRequested"
    )
    review_tampered[review_index]["payload"]["subject_sha256"] = "8" * 64
    with pytest.raises(AuthorityRejected, match="subject_hash_mismatch"):
        replay_authority(review_tampered)

    with pytest.raises(AuthorityRejected, match="invalid_owner_resolution"):
        prepare_authority_transition(
            events=registered,
            kind="path_registration",
            action="resolve",
            actor_id=OWNER,
            payload={"decision_id": "premature", "decision": "accept", "transaction_id": "premature"},
        )

    with pytest.raises(AuthorityRejected, match="already_accepted"):
        prepare_authority_transition(
            events=events,
            kind="path_registration",
            action="resolve",
            actor_id=OWNER,
            payload={"decision_id": "dec_path_registration", "decision": "accept", "transaction_id": "again"},
        )

    stale = _subject("dossier_expected_set")
    stale["record_revision"] = 0
    stale["subject_sha256"] = subject_sha256(stale)
    with pytest.raises(AuthorityRejected, match="stale_revision"):
        prepare_authority_transition(
            events=(), kind="dossier_expected_set", action="register", actor_id=AUTHOR, payload={"subject": stale}
        )

    collision = _subject("path_registration")
    collision["collision_status"] = "collision"
    collision["subject_sha256"] = subject_sha256(collision)
    with pytest.raises(AuthorityRejected, match="path_collision"):
        prepare_authority_transition(
            events=(), kind="path_registration", action="register", actor_id=AUTHOR, payload={"subject": collision}
        )
