# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-2; P-081, P-083)
# Purpose: LR-016 to LR-020 through the real LegacyRuntime.submit on scratch stores and scratch Git repositories: the
# accepted batch, the window (O-33, W9-T6), the anchors (W9-T16), the change list (O-32) and the role rules.
"""WP9.3-2 runtime tests (WP9.3 note §6.2, §7.2, §10, §17).

Every store is a scratch store under ``tmp_path``; every source is in a scratch Git repository under ``tmp_path``. A
refusal before append is checked with the ledger and the control root byte-identical, directories included, and with
the refusing check's own message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from research_system.errors import IntegrityError
from research_system.legacy import evidence
from research_system.legacy.replay.driver import replay_legacy
from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes
from tests.research_system.integration.w9_runtime_harness import OWNER, W9Store, git, w9_store

UNTRACKED = b"note\n"
RESTRICTED = b"\x80\x04restricted"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> W9Store:
    return w9_store(tmp_path, monkeypatch)


def _state(store: W9Store) -> dict[str, Any]:
    return replay_legacy(store.events(), schemas=store.harness.schemas, pinned_signatures=(store.pin,))


def _unchanged(store: W9Store) -> tuple[tuple, dict]:
    return store.events(), _tree_bytes(store.runtime.control_root)


def _whole(store: W9Store) -> str:
    """results/x.json registered and observed whole (git_tracked)."""
    registration = store.register("results/x.json")
    receipt, observation_id = store.observe(store.observation_payload(registration))
    assert receipt.status == "accepted"
    return observation_id


def _untracked(store: W9Store) -> tuple[str, Path, dict[str, Any]]:
    path = store.repo / "notes" / "untracked.md"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(UNTRACKED)
    registration = store.register("notes/untracked.md", kind="untracked_file", role="legacy_coordination")
    payload = store.observation_payload(registration)
    payload["frozen_copy_ref"] = store.frozen_copy(UNTRACKED, "untracked.md")
    receipt, observation_id = store.observe(payload)
    assert receipt.status == "accepted"
    return observation_id, path, registration


def _restricted(store: W9Store) -> tuple[str, Path, dict[str, Any]]:
    path = store.repo / "data" / "rows.pkl"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(RESTRICTED)
    registration = store.register("data/rows.pkl", kind="restricted_untracked_file", role="legacy_research_result")
    receipt, observation_id = store.observe(store.observation_payload(registration))
    assert receipt.status == "accepted"
    return observation_id, path, registration


def _refused_at(store: W9Store, record: dict[str, Any], message: str, *, stop_after: str | None = None) -> None:
    """Run the batch up to the refusing step; that step's command raises with ``message`` and changes nothing."""
    if stop_after is not None:
        assert store.accept(record, stop_after=stop_after).status == "accepted"
    before = _unchanged(store)
    with pytest.raises(IntegrityError, match=message):
        if stop_after is None:
            store.accept(record)
        else:
            decision_id = record["decision_ref"]["id"]
            store.submit(
                "ResolveW9AuthorityDecision",
                OWNER,
                decision_id,
                1,
                {"decision_id": decision_id, "selected_option": "accept"},
            )
    assert _unchanged(store) == before


# --- The accepted batch -----------------------------------------------------------------------------------------------


def test_an_accepted_batch_through_submit_closes_its_whole_file_registration(store: W9Store) -> None:
    observation_id = _whole(store)
    record = store.acceptance_payload([observation_id])
    receipt = store.accept(record)
    assert receipt.status == "accepted"
    state = _state(store)
    acceptance = state["records"]["legacy_closed_reference_acceptance"][record["record_id"]]
    assert acceptance["created_by_actor_id"] == store.actors.analyst
    [transition] = state["records"]["legacy_ownership_transitioned"].values()
    assert transition == state["proposals"][record["record_id"]]["ownership"][0]
    registration_id = acceptance["items"][0]["observation_ref"]["id"]
    observation = state["records"]["legacy_observation"][registration_id]
    assert state["ownership"] == {observation["registration_ref"]["id"]: "closed_reference"}


def test_w9_c11_each_acceptance_step_retried_is_answered_from_receipts(store: W9Store) -> None:
    """W9-C11: an exact retry of each of LR-016 to LR-020 is answered from its receipt, with nothing appended."""
    record = store.acceptance_payload([_whole(store)])
    assert store.accept(record).status == "accepted"
    steps = [
        entry
        for entry in store.log
        if entry[0]["payload"] in (record,)
        or entry[0]["target_stream_id"]
        in {record["record_id"], record["independent_review_ref"]["id"], record["decision_ref"]["id"]}
    ]
    assert len(steps) == 5
    events = store.events()
    for envelope, receipt in steps:
        retried = store.runtime.submit(envelope)
        assert retried.status == receipt.status == "accepted"
        assert (retried.command_id, retried.event_batch_id) == (receipt.command_id, receipt.event_batch_id)
    assert store.events() == events


def test_the_owner_is_refused_on_lr016_and_a_non_owner_on_lr020(store: W9Store) -> None:
    """§5.5: Stephen resolves; he does not propose. The resolver row requires him."""
    record = store.acceptance_payload([_whole(store)])
    before = _unchanged(store)
    with pytest.raises(IntegrityError, match="W9 LR-016 refuses the owner"):
        store.submit("ProposeLegacyRecord", OWNER, record["record_id"], 0, record)
    assert _unchanged(store) == before
    assert store.accept(record, stop_after="LR-019").status == "accepted"
    decision_id = record["decision_ref"]["id"]
    before = _unchanged(store)
    with pytest.raises(IntegrityError, match="W9 LR-020 is resolved by the owner only"):
        store.submit(
            "ResolveW9AuthorityDecision",
            store.actors.analyst,
            decision_id,
            1,
            {"decision_id": decision_id, "selected_option": "accept"},
        )
    assert _unchanged(store) == before


# --- The window: W9-T6 and O-33 (§7.2) --------------------------------------------------------------------------------


def test_w9_t6_a_source_changed_after_observation_refuses_lr016(store: W9Store) -> None:
    observation_id, path, _ = _untracked(store)
    path.write_bytes(b"edited after the observation\n")
    _refused_at(store, store.acceptance_payload([observation_id]), "W9 acceptance item's source re-reads differently")


def test_w9_t6_a_source_changed_between_lr016_and_lr020_refuses_lr020(store: W9Store) -> None:
    observation_id, path, _ = _untracked(store)
    record = store.acceptance_payload([observation_id])
    assert store.accept(record, stop_after="LR-019").status == "accepted"
    path.write_bytes(b"edited after the proposal\n")
    decision_id = record["decision_ref"]["id"]
    before = _unchanged(store)
    with pytest.raises(IntegrityError, match="W9 acceptance item's source re-reads differently"):
        store.submit(
            "ResolveW9AuthorityDecision",
            OWNER,
            decision_id,
            1,
            {"decision_id": decision_id, "selected_option": "accept"},
        )
    assert _unchanged(store) == before
    assert _state(store)["stale_observations"] == []  # a failed re-read leaves no event, so nothing is stale


def test_o33_a_change_in_lr016s_gap_commits_and_lr020_then_refuses_it(store: W9Store) -> None:
    """§7.2: a change between LR-016's final re-read and its append is a change after the proposal; the proposal
    commits, LR-020's re-read refuses the changed source, and the projection marks nothing stale."""
    observation_id, path, _ = _untracked(store)
    record = store.acceptance_payload([observation_id])
    store.runtime.binding_check = lambda: path.write_bytes(b"edited in LR-016's gap\n")
    assert store.accept(record, stop_after="LR-016").status == "accepted"
    store.runtime.binding_check = None
    store.review(record, record["independent_review_ref"]["id"], store.actors.reviewer, author_session=False)
    decision_id = record["decision_ref"]["id"]
    decide = {"subject_record_id": record["record_id"], "question": "?", "recommendation": "accept", "consequences": []}
    assert store.submit("ProposeW9AuthorityDecision", store.actors.analyst, decision_id, 0, decide).status == "accepted"
    before = _unchanged(store)
    with pytest.raises(IntegrityError, match="W9 acceptance item's source re-reads differently"):
        store.submit(
            "ResolveW9AuthorityDecision",
            OWNER,
            decision_id,
            1,
            {"decision_id": decision_id, "selected_option": "accept"},
        )
    assert _unchanged(store) == before
    assert _state(store)["stale_observations"] == []


def test_o33_a_change_in_lr020s_gap_is_a_change_after_acceptance(store: W9Store) -> None:
    """§7.2: the acceptance commits naming the recorded hashes, the frozen copy still hashes to them, and a following
    observation of the registration records the new hash and makes the accepted record stale."""
    observation_id, path, registration = _untracked(store)
    record = store.acceptance_payload([observation_id])
    assert store.accept(record, stop_after="LR-019").status == "accepted"
    store.runtime.binding_check = lambda: path.write_bytes(b"edited in LR-020's gap\n")
    decision_id = record["decision_ref"]["id"]
    resolve = {"decision_id": decision_id, "selected_option": "accept"}
    assert store.submit("ResolveW9AuthorityDecision", OWNER, decision_id, 1, resolve).status == "accepted"
    store.runtime.binding_check = None
    state = _state(store)
    observation = state["records"]["legacy_observation"][observation_id]
    assert observation["source_identity"]["sha256"] == record_sha(UNTRACKED)
    from research_system.legacy.preparers import Environment, check_frozen_copy

    generic = store.runtime._replay(store.events())[0]
    check_frozen_copy(
        Environment(store.runtime.reader, generic, store.harness.ledger.control_root, None),
        observation["source_identity"]["frozen_copy_ref"],
        observation["source_identity"]["sha256"],
        observation["source_identity"]["byte_length"],
    )
    later = store.observation_payload(registration)
    later["frozen_copy_ref"] = store.frozen_copy(path.read_bytes(), "untracked-later.md")
    receipt, _ = store.observe(later)
    assert receipt.status == "accepted"
    assert observation_id in _state(store)["stale_observations"]


def test_o33_a_restricted_item_is_accepted_on_its_recorded_hash_with_no_copy(store: W9Store) -> None:
    observation_id, path, registration = _restricted(store)
    record = store.acceptance_payload([observation_id])
    assert store.accept(record, stop_after="LR-019").status == "accepted"
    store.runtime.binding_check = lambda: path.write_bytes(b"\x80\x04edited in the gap")
    decision_id = record["decision_ref"]["id"]
    resolve = {"decision_id": decision_id, "selected_option": "accept"}
    assert store.submit("ResolveW9AuthorityDecision", OWNER, decision_id, 1, resolve).status == "accepted"
    store.runtime.binding_check = None
    state = _state(store)
    assert record["record_id"] in state["records"]["legacy_closed_reference_acceptance"]
    receipt, _ = store.observe(store.observation_payload(registration))
    assert receipt.status == "accepted"
    assert observation_id in _state(store)["stale_observations"]


@pytest.mark.parametrize("damage", ["deleted", "altered"])
def test_lr020_refuses_a_frozen_copy_deleted_or_altered_before_its_re_check(store: W9Store, damage: str) -> None:
    """§7.2 (P-081 O-33 addition, 2026-11-09): a missing or altered copy aborts LR-020 with no event and no receipt,
    and a restricted item in the same batch is not refused for having no copy."""
    observation_id, _, _ = _untracked(store)
    restricted_id, _, _ = _restricted(store)
    record = store.acceptance_payload([observation_id, restricted_id])
    assert store.accept(record, stop_after="LR-019").status == "accepted"
    copy = store.harness.ledger.control_root / "evidence" / "w9-frozen" / "untracked.md"
    assert copy.is_file()
    if damage == "deleted":
        copy.unlink()
        message = "W9 frozen copy cannot be read"
    else:
        copy.write_bytes(b"altered copy\n")
        message = "W9 frozen copy bytes differ from the observed bytes"
    decision_id = record["decision_ref"]["id"]
    before = _unchanged(store)
    with pytest.raises(IntegrityError, match=message):
        store.submit(
            "ResolveW9AuthorityDecision",
            OWNER,
            decision_id,
            1,
            {"decision_id": decision_id, "selected_option": "accept"},
        )
    assert _unchanged(store) == before


def test_a_restricted_item_alongside_an_intact_copy_is_accepted(store: W9Store) -> None:
    observation_id, _, _ = _untracked(store)
    restricted_id, _, _ = _restricted(store)
    assert store.accept(store.acceptance_payload([observation_id, restricted_id])).status == "accepted"


def record_sha(raw: bytes) -> str:
    import hashlib

    return hashlib.sha256(raw).hexdigest()


# --- The anchors: W9-T16 (§10.3) --------------------------------------------------------------------------------------


def test_w9_t16_an_anchor_commit_that_is_not_an_ancestor_of_git_head_is_refused(store: W9Store) -> None:
    observation_id = _whole(store)
    git(store.repo, "checkout", "-q", "-b", "side")
    (store.repo / "side.md").write_text("side\n", encoding="utf-8")
    git(store.repo, "add", "side.md")
    git(store.repo, "commit", "-q", "-m", "side")
    side = git(store.repo, "rev-parse", "HEAD")
    git(store.repo, "checkout", "-q", "-")
    record = store.acceptance_payload([observation_id], anchor_commit=side)
    _refused_at(store, record, "W9 acceptance anchor commit is not an ancestor of git_head")


def test_w9_t16_an_ancestor_commit_that_does_not_introduce_the_hashed_bytes_is_refused(store: W9Store) -> None:
    observation_id = _whole(store)
    (store.repo / "later.md").write_text("later\n", encoding="utf-8")
    git(store.repo, "add", "later.md")
    git(store.repo, "commit", "-q", "-m", "later")
    later = store.rebind()
    record = store.acceptance_payload([observation_id], anchor_commit=later)
    _refused_at(store, record, "W9 acceptance anchor commit does not introduce the anchored bytes")


def test_w9_t16_an_ars_event_anchor_is_refused(store: W9Store) -> None:
    from research_system.ids import new_id

    observation_id = _whole(store)
    record = store.acceptance_payload([observation_id])
    record["anchors"][0] = {
        "anchored": "threshold_preregistration",
        "anchor_kind": "ars_event",
        "value": new_id("event"),
    }
    _refused_at(store, record, r"W9 acceptance anchor must be a git_commit anchor \(owner point G\)")


def test_a_git_tracked_item_observed_at_an_earlier_head_is_accepted_after_the_binding_moves(store: W9Store) -> None:
    """Reading R10: the re-read compares location and bytes, not the commit, because a later head moves the commit
    but not the blob (§7.2)."""
    observation_id = _whole(store)
    (store.repo / "docs.md").write_text("a docs-only commit\n", encoding="utf-8")
    git(store.repo, "add", "docs.md")
    git(store.repo, "commit", "-q", "-m", "docs")
    store.rebind()
    assert store.accept(store.acceptance_payload([observation_id])).status == "accepted"


# --- The change list: O-32 (§10.4) ------------------------------------------------------------------------------------


def _commit_changes(store: W9Store, *entries: dict[str, Any]) -> str:
    body = {"format": evidence.SHARED_SURFACE_CHANGES_FORMAT, "entries": list(entries)}
    (store.repo / evidence.SHARED_SURFACE_CHANGES).write_text(json.dumps(body), encoding="utf-8")
    git(store.repo, "add", evidence.SHARED_SURFACE_CHANGES)
    git(store.repo, "commit", "-q", "-m", "change list")
    return store.rebind()


def _affects(merge_commit: str, path: str) -> dict[str, Any]:
    return {
        "merge_commit": merge_commit,
        "surface": "a shared surface",
        "affected_registrations": [{"root_kind": "repository_root", "root_id": "repository", "normalized_path": path}],
    }


def test_o32_an_item_observed_after_the_change_that_affects_it_is_admitted(store: W9Store) -> None:
    root = git(store.repo, "rev-list", "--max-parents=0", "HEAD")
    observation_id = _whole(store)  # observed at the root commit, which descends from (is) the merge commit
    _commit_changes(store, _affects(root, "results/x.json"), _affects(root, "tracker.md"))
    assert store.accept(store.acceptance_payload([observation_id])).status == "accepted"


def test_o32_an_item_that_predates_a_change_affecting_it_is_refused(store: W9Store) -> None:
    observation_id = _whole(store)
    (store.repo / "surface.md").write_text("the change\n", encoding="utf-8")
    git(store.repo, "add", "surface.md")
    git(store.repo, "commit", "-q", "-m", "shared surface change")
    merged = git(store.repo, "rev-parse", "HEAD")
    _commit_changes(store, _affects(merged, "results/x.json"))
    _refused_at(
        store,
        store.acceptance_payload([observation_id]),
        "W9 acceptance item predates a shared-surface change that affects it",
    )


def test_o32_an_affected_item_that_is_not_git_tracked_is_refused(store: W9Store) -> None:
    observation_id, _, _ = _untracked(store)
    root = git(store.repo, "rev-list", "--max-parents=0", "HEAD")
    _commit_changes(store, _affects(root, "notes/untracked.md"))
    _refused_at(
        store,
        store.acceptance_payload([observation_id]),
        "W9 acceptance item affected by a shared-surface change is not git_tracked",
    )


def test_o32_a_change_list_ref_that_is_not_the_list_at_git_head_is_refused(store: W9Store) -> None:
    observation_id = _whole(store)
    record = store.acceptance_payload([observation_id])  # names the list's blob at the current head
    (store.repo / evidence.SHARED_SURFACE_CHANGES).write_text(
        json.dumps({"format": evidence.SHARED_SURFACE_CHANGES_FORMAT, "entries": [_affects("a" * 40, "x")]}),
        encoding="utf-8",
    )
    git(store.repo, "commit", "-q", "-am", "list v2")
    store.rebind()
    _refused_at(store, record, "W9 shared-surface change list is not the list at git_head")


def test_o32_an_absent_change_list_refuses_lr016(store: W9Store) -> None:
    observation_id = _whole(store)
    record = store.acceptance_payload([observation_id])
    git(store.repo, "rm", "-q", evidence.SHARED_SURFACE_CHANGES)
    git(store.repo, "commit", "-q", "-m", "no list")
    store.rebind()
    _refused_at(store, record, "W9 evidence file is absent at git_head")
