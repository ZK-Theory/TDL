"""Negative controls for the merge-admission gates.

Each gate ships a watched failure. The primary one is not synthetic: the
committed PR #262 snapshot is the exact evidence that admitted the merge these
gates exist to prevent, so both gates are asserted to refuse it. Paired
positive controls mutate only the offending fact, which keeps a passing gate
from being vacuous.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import statistics
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from tools.check_merge_admission import (
    SWEEP_MAX_RUN_AGE,
    SweepGate,
    evaluate_merge_group_size,
    evaluate_platform_order,
    evaluate_sweep_cadence,
    evaluate_thread_finality,
    evidence_is_stale,
    load_config,
    main,
    path_is_sensitive,
    platform_producer,
    platform_status,
    queue_disposition,
    sweep_actions,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".github" / "merge-admission.yml"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "merge-admission.yml"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pr262_merge_candidate_snapshot.json"

PR262_CANDIDATE = "af680b81f10df2bf0f0803a475e34656a926f766"
PR262_LAST_CLEAN_READBACK = "2026-08-23T07:28:14Z"
PR262_LATE_THREADS_AT = "2026-08-23T07:40:23Z"


@pytest.fixture
def config() -> dict[str, Any]:
    """Return the committed merge-admission configuration."""
    return dict(load_config(CONFIG_PATH))


@pytest.fixture
def snapshot() -> dict[str, Any]:
    """Return a mutable copy of the recorded PR #262 candidate snapshot."""
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _pull_request(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the mutable pullRequest object inside a snapshot copy."""
    return snapshot["data"]["repository"]["pullRequest"]


def _thread_finality(snapshot: dict[str, Any], config: dict[str, Any], *, candidate: str = PR262_CANDIDATE) -> None:
    """Run the thread-finality gate with the committed producer list."""
    evaluate_thread_finality(
        snapshot,
        candidate_sha=candidate,
        review_producers=config["thread_finality"]["review_producers"],
    )


def _platform_kwargs(config: dict[str, Any], candidate: str, platform: str | None) -> dict[str, Any]:
    """Return the shared keyword arguments for both platform evaluators."""
    return {
        "candidate_sha": candidate,
        "platform_sha": platform or candidate,
        "producer": platform_producer(config),
        "sensitive_paths": config["platform_order"]["sensitive_paths"],
    }


def _platform_order(
    snapshot: dict[str, Any],
    config: dict[str, Any],
    *,
    candidate: str = PR262_CANDIDATE,
    platform: str | None = None,
) -> str:
    """Run the platform-order gate with the committed path and job config."""
    return evaluate_platform_order(snapshot, **_platform_kwargs(config, candidate, platform))


def _platform_status(snapshot: dict[str, Any], config: dict[str, Any], *, platform: str | None = None) -> str:
    """Run the platform-status probe the workflow uses to decide whether to wait."""
    return platform_status(snapshot, **_platform_kwargs(config, PR262_CANDIDATE, platform))


# --------------------------------------------------------------------------
# thread-finality (observation 01M0PWSR73ABY48X8YW7KQX6Q6)
# --------------------------------------------------------------------------


def test_recorded_pr262_candidate_is_refused_admission(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The historical merge that motivated this gate must not be admissible."""
    with pytest.raises(ValueError, match="unresolved non-outdated review thread"):
        _thread_finality(snapshot, config)


def test_five_codex_threads_are_the_sole_cause_of_the_block(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Removing exactly the five late threads admits; the gate is not vacuous."""
    pull_request = _pull_request(snapshot)
    threads = pull_request["reviewThreads"]["nodes"]
    live = [thread for thread in threads if not thread["isResolved"] and not thread["isOutdated"]]
    assert len(live) == 5, "fixture must retain the five threads published 89s before the merge"

    pull_request["reviewThreads"]["nodes"] = [thread for thread in threads if thread not in live]
    _thread_finality(snapshot, config)


def test_a_late_thread_invalidates_prior_clean_evidence(snapshot: dict[str, Any]) -> None:
    """Clean-thread evidence is only evidence for the moment it was taken."""
    assert evidence_is_stale(snapshot, evidence_recorded_at=PR262_LAST_CLEAN_READBACK) is True
    assert evidence_is_stale(snapshot, evidence_recorded_at=PR262_LATE_THREADS_AT) is False


def test_a_producer_that_has_not_reviewed_the_candidate_blocks(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """A configured producer short of terminal state blocks, never passes."""
    pull_request = _pull_request(snapshot)
    pull_request["reviews"]["nodes"] = [
        review
        for review in pull_request["reviews"]["nodes"]
        if not (review["author"]["login"] == "chatgpt-codex-connector" and review["commit"]["oid"] == PR262_CANDIDATE)
    ]
    with pytest.raises(ValueError, match="have not reached a terminal state"):
        _thread_finality(snapshot, config)


def test_evidence_from_an_earlier_head_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """A snapshot that does not describe the candidate is not admission evidence."""
    with pytest.raises(ValueError, match="is not the merge candidate"):
        _thread_finality(snapshot, config, candidate="7df10de65eed3dd7e3668bf4bbe5c291aabb161d")


def test_truncated_thread_evidence_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Partial evidence fails closed rather than admitting on the visible page."""
    _pull_request(snapshot)["reviewThreads"]["pageInfo"]["hasNextPage"] = True
    with pytest.raises(ValueError, match="truncated"):
        _thread_finality(snapshot, config)


def test_codex_is_the_only_required_review_producer(config: dict[str, Any]) -> None:
    """Decided 2026-09-11: CodeRabbit skipped most PRs, so requiring it would block nearly every merge."""
    assert config["thread_finality"]["review_producers"] == ["chatgpt-codex-connector"]


def test_a_coderabbit_thread_still_blocks_without_coderabbit_being_required(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Dropping a producer requirement must not drop its threads: finality ignores thread authorship."""
    threads = _pull_request(snapshot)["reviewThreads"]["nodes"]
    for thread in threads:
        if thread["comments"]["nodes"][0]["author"]["login"] == "chatgpt-codex-connector":
            thread["isResolved"] = True
    live_rabbit = next(t for t in threads if t["comments"]["nodes"][0]["author"]["login"] == "coderabbitai")
    live_rabbit.update({"isResolved": False, "isOutdated": False})
    with pytest.raises(ValueError, match="from coderabbitai"):
        _thread_finality(snapshot, config)


def test_a_graphql_error_response_is_refused(config: dict[str, Any]) -> None:
    """A failed query is absence of evidence, not evidence of a clean candidate."""
    with pytest.raises(ValueError, match="carries errors"):
        evaluate_thread_finality(
            {"errors": [{"message": "rate limited"}]},
            candidate_sha=PR262_CANDIDATE,
            review_producers=config["thread_finality"]["review_producers"],
        )


# --------------------------------------------------------------------------
# producer states: a clean +1, quota, untriggered (obs 2026-09-17-merge-admission-
# cannot-see-a-clean-codex-review, 2026-09-11-required-review-producer-is-quota-limited)
# --------------------------------------------------------------------------

FIRST_CHECK_STARTED = "2026-08-23T07:30:00Z"
CODEX_BOT = "chatgpt-codex-connector[bot]"
QUOTA_BODY = "You have reached your Codex usage limits for code reviews. You can see your limits in the dashboard."


def _without_codex_review(snapshot: dict[str, Any], *, started_at: str | None = FIRST_CHECK_STARTED) -> dict[str, Any]:
    """The candidate with every thread resolved and no Codex review object on it.

    ``started_at`` stamps the candidate's check runs; ``None`` leaves them unstarted.
    """
    pull_request = _pull_request(snapshot)
    for thread in pull_request["reviewThreads"]["nodes"]:
        thread["isResolved"] = True
    pull_request["reviews"]["nodes"] = [
        review
        for review in pull_request["reviews"]["nodes"]
        if not (review["author"]["login"] == "chatgpt-codex-connector" and review["commit"]["oid"] == PR262_CANDIDATE)
    ]
    for context in _head_rollup(snapshot):
        if context.get("__typename") == "CheckRun":
            context["startedAt"] = started_at
    pull_request["reactions"] = {"pageInfo": {"hasNextPage": False}, "nodes": []}
    pull_request["comments"] = {"pageInfo": {"hasPreviousPage": False}, "nodes": []}
    return snapshot


def _react(snapshot: dict[str, Any], *, at: str, login: str = CODEX_BOT, content: str = "THUMBS_UP") -> dict[str, Any]:
    _pull_request(snapshot)["reactions"]["nodes"].append(
        {"content": content, "createdAt": at, "user": {"login": login}}
    )
    return snapshot


def _comment(snapshot: dict[str, Any], *, at: str, body: str, login: str = "chatgpt-codex-connector") -> dict[str, Any]:
    _pull_request(snapshot)["comments"]["nodes"].append({"createdAt": at, "body": body, "author": {"login": login}})
    return snapshot


def test_a_codex_plus_one_after_the_candidates_first_check_admits(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Codex's clean signal is a reaction, not a review; one made after this head arrived is terminal."""
    _react(_without_codex_review(snapshot), at="2026-08-23T07:35:12Z")
    _thread_finality(snapshot, config)


def test_a_stale_plus_one_from_an_earlier_head_still_blocks(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The decided negative control: a +1 older than the candidate's first check describes another head."""
    _react(_without_codex_review(snapshot), at="2026-08-23T07:10:00Z")
    with pytest.raises(ValueError, match=r"\+1 predates this head.*@codex review"):
        _thread_finality(snapshot, config)


def test_a_plus_one_cannot_be_bound_when_no_check_has_started(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """With no started check there is no lower bound on the push time, so the reaction binds to nothing."""
    _react(_without_codex_review(snapshot, started_at=None), at="2026-08-23T07:35:12Z")
    with pytest.raises(ValueError, match="no check run has started"):
        _thread_finality(snapshot, config)


def test_another_users_plus_one_is_not_a_codex_signal(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    _react(_without_codex_review(snapshot), at="2026-08-23T07:35:12Z", login="stephendor")
    with pytest.raises(ValueError, match="has not reviewed or reacted on this head"):
        _thread_finality(snapshot, config)


def test_a_non_thumbs_up_reaction_is_not_a_clean_signal(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    _react(_without_codex_review(snapshot), at="2026-08-23T07:35:12Z", content="EYES")
    with pytest.raises(ValueError, match="has not reviewed or reacted on this head"):
        _thread_finality(snapshot, config)


def test_a_codex_review_naming_another_commit_after_the_push_voids_the_plus_one(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """A later review of a different commit makes the reaction's target ambiguous; it must not admit."""
    _react(_without_codex_review(snapshot), at="2026-08-23T07:35:12Z")
    _pull_request(snapshot)["reviews"]["nodes"].append(
        {
            "state": "COMMENTED",
            "submittedAt": "2026-08-23T07:36:00Z",
            "author": {"login": "chatgpt-codex-connector"},
            "commit": {"oid": "7df10de65eed3dd7e3668bf4bbe5c291aabb161d"},
        }
    )
    with pytest.raises(ValueError, match="names another commit"):
        _thread_finality(snapshot, config)


def test_a_foreign_review_older_than_the_accepted_plus_one_does_not_void_it(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """A review of the previous commit that lands after this head's first check but before the +1 is older than
    the signal being accepted; only a review after the +1 makes its target ambiguous."""
    _react(_without_codex_review(snapshot), at="2026-08-23T07:40:00Z")
    _pull_request(snapshot)["reviews"]["nodes"].append(
        {
            "state": "COMMENTED",
            "submittedAt": "2026-08-23T07:32:00Z",
            "author": {"login": "chatgpt-codex-connector"},
            "commit": {"oid": "7df10de65eed3dd7e3668bf4bbe5c291aabb161d"},
        }
    )
    _thread_finality(snapshot, config)


def test_quota_on_this_head_outranks_a_stale_plus_one(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """An earlier head's +1 must not hide that this head hit the usage limit: the remedy differs."""
    _react(_without_codex_review(snapshot), at="2026-08-23T07:10:00Z")
    _comment(snapshot, at="2026-08-23T07:31:00Z", body=QUOTA_BODY)
    with pytest.raises(ValueError, match=r"usage limit.*waiver"):
        _thread_finality(snapshot, config)


def test_a_comment_window_that_cannot_reach_this_heads_arrival_is_not_called_untriggered(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """More than 50 comments since the push: a quota reply may be in the unfetched part, so the state is unknown."""
    _comment(_without_codex_review(snapshot), at="2026-08-23T07:50:00Z", body="a later discussion comment")
    _pull_request(snapshot)["comments"]["pageInfo"]["hasPreviousPage"] = True
    with pytest.raises(ValueError, match="usage limit is unknown"):
        _thread_finality(snapshot, config)


def test_a_comment_window_that_reaches_back_past_this_heads_arrival_is_complete(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Earlier pages exist, but the fetched window already covers everything since the push."""
    _comment(_without_codex_review(snapshot), at="2026-08-23T07:00:00Z", body="an older comment")
    _pull_request(snapshot)["comments"]["pageInfo"]["hasPreviousPage"] = True
    with pytest.raises(ValueError, match="has not reviewed or reacted on this head"):
        _thread_finality(snapshot, config)


def test_a_usage_limit_on_this_head_is_named_with_its_remedy(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Quota is not 'still reviewing': the head will never be reviewed automatically."""
    _comment(_without_codex_review(snapshot), at="2026-08-23T07:31:00Z", body=QUOTA_BODY)
    with pytest.raises(ValueError, match=r"usage limit.*@codex review.*waiver"):
        _thread_finality(snapshot, config)


def test_a_usage_limit_on_an_earlier_head_does_not_label_this_one(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """A quota comment older than this head's first check was about another head: this one is untriggered."""
    _comment(_without_codex_review(snapshot), at="2026-08-23T07:00:00Z", body=QUOTA_BODY)
    with pytest.raises(ValueError, match="has not reviewed or reacted on this head"):
        _thread_finality(snapshot, config)


def test_an_untriggered_head_names_its_remedy(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    _without_codex_review(snapshot)
    with pytest.raises(ValueError, match=r"has not reviewed or reacted on this head.*@codex review"):
        _thread_finality(snapshot, config)


def test_a_clean_plus_one_does_not_excuse_a_live_thread(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The +1 settles the producer; thread finality is still judged separately."""
    _react(_without_codex_review(snapshot), at="2026-08-23T07:35:12Z")
    _pull_request(snapshot)["reviewThreads"]["nodes"][0].update({"isResolved": False, "isOutdated": False})
    with pytest.raises(ValueError, match="unresolved non-outdated review thread"):
        _thread_finality(snapshot, config)


def test_the_admission_snapshot_requests_reactions_comments_and_check_start_times() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "reactions(first:100, content:THUMBS_UP)" in workflow
    assert "comments(last:50){ pageInfo{hasPreviousPage}" in workflow
    assert "startedAt" in workflow


# --------------------------------------------------------------------------
# platform-order (observation 01M0Q0WXJSCX5WJ69H2G9DG4E3)
# --------------------------------------------------------------------------


MERGE_GROUP_SHA = "0123456789abcdef0123456789abcdef01234567"
MERGE_GROUP_BASE = "fedcba9876543210fedcba9876543210fedcba98"
TRUSTED_SUITE = {"app": {"slug": "github-actions"}, "workflowRun": {"file": {"path": ".github/workflows/ci.yml"}}}
DOCS_ONLY = [{"filename": "docs/plans/strategy/Meta-Research-Plan.md", "previous_filename": None, "status": "modified"}]


def _head_rollup(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the mutable check contexts on the pull request head."""
    commit = _pull_request(snapshot)["commits"]["nodes"][0]["commit"]
    return commit["statusCheckRollup"]["contexts"]["nodes"]


def _platform_run(
    *,
    completed_at: str | None,
    conclusion: str | None = "SUCCESS",
    status: str = "COMPLETED",
    suite: dict[str, Any] | None = None,
    database_id: int = 900,
) -> dict[str, Any]:
    """Return a `windows-store-lock` check run, trusted unless ``suite`` says otherwise."""
    return {
        "__typename": "CheckRun",
        "databaseId": database_id,
        "name": "windows-store-lock",
        "status": status,
        "conclusion": conclusion,
        "completedAt": completed_at,
        "checkSuite": copy.deepcopy(TRUSTED_SUITE if suite is None else suite),
    }


def _with_head_run(snapshot: dict[str, Any], **run: Any) -> dict[str, Any]:
    """Return the snapshot with a platform run attached to the pull request head."""
    _head_rollup(snapshot).append(_platform_run(**run))
    return snapshot


def _with_approval(snapshot: dict[str, Any], *, submitted_at: str, login: str = "stephendor") -> dict[str, Any]:
    """Return the snapshot with an approving review on the candidate."""
    _pull_request(snapshot)["reviews"]["nodes"].append(
        {
            "state": "APPROVED",
            "submittedAt": submitted_at,
            "author": {"login": login},
            "commit": {"oid": PR262_CANDIDATE},
        }
    )
    return snapshot


def _with_files(snapshot: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the snapshot with its REST file listing replaced, keeping the count consistent."""
    snapshot["restFiles"] = copy.deepcopy(rows)
    _pull_request(snapshot)["changedFiles"] = len(rows)
    return snapshot


def _as_merge_group(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the snapshot with a merge-group commit that has no checks yet."""
    snapshot["data"]["repository"]["platformCommit"] = {
        "oid": MERGE_GROUP_SHA,
        "statusCheckRollup": {"contexts": {"pageInfo": {"hasNextPage": False}, "nodes": []}},
    }
    return snapshot


def _with_queue_run(snapshot: dict[str, Any], **run: Any) -> dict[str, Any]:
    """Return the snapshot with a platform run attached to the merge-group commit."""
    snapshot["data"]["repository"]["platformCommit"]["statusCheckRollup"]["contexts"]["nodes"].append(
        _platform_run(**run)
    )
    return snapshot


def _approved_after_green_head(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the snapshot in its correctly ordered, admissible state."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    return _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")


def test_store_changes_without_a_platform_run_are_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """PR #262 changed store code with no platform job on the candidate at all."""
    with pytest.raises(ValueError, match=f"no 'windows-store-lock' check run on {PR262_CANDIDATE}"):
        _platform_order(snapshot, config)


def test_platform_order_does_not_apply_to_untouched_surfaces(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """A candidate outside the configured surfaces is not subject to ordering."""
    _with_files(snapshot, DOCS_ONLY)
    assert "not applicable" in _platform_order(snapshot, config)


def test_approval_before_platform_evidence_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The PR #263 shape: acceptance recorded ahead of the decisive platform run."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:10:00Z")
    with pytest.raises(ValueError, match="approval preceded platform evidence"):
        _platform_order(snapshot, config)


def test_approval_after_green_platform_evidence_is_admitted(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The corrected ordering passes, so the block above is caused by ordering."""
    verdict = _platform_order(_approved_after_green_head(snapshot), config)
    assert "research_system/store/lock.py" in verdict


def test_a_failing_platform_run_is_refused_regardless_of_ordering(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Ordering is necessary, not sufficient: the platform evidence must be green."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z", conclusion="FAILURE")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    with pytest.raises(ValueError, match="concluded 'FAILURE'"):
        _platform_order(snapshot, config)


# Codex review 3962013244: a superseded early approval must not keep the gate blocked.


def test_a_reapproval_after_green_platform_supersedes_the_early_one(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """The gate's own remediation -- re-request review -- must actually clear it."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:10:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    assert "green before approval" in _platform_order(snapshot, config)


def test_another_reviewers_early_approval_still_blocks(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Supersession is per reviewer: one reviewer's re-approval does not clear another's."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:10:00Z", login="independent-reviewer")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    with pytest.raises(ValueError, match="independent-reviewer at 2026-08-23T07:10:00Z"):
        _platform_order(snapshot, config)


# Codex review 3988684687: queue health and approval ordering are separate questions.


def test_a_queued_candidate_approved_before_queue_ci_is_admitted(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """The real queue flow: approval precedes the queue commit's run, and that is fine."""
    _as_merge_group(_approved_after_green_head(snapshot))
    _with_queue_run(snapshot, completed_at="2026-08-23T09:00:00Z")
    verdict = _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)
    assert f"also green on merge-group commit {MERGE_GROUP_SHA}" in verdict


def test_a_queued_candidate_is_refused_when_the_queue_commit_fails(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """An integration-only failure blocks, even with a green, correctly ordered head."""
    _as_merge_group(_approved_after_green_head(snapshot))
    _with_queue_run(snapshot, completed_at="2026-08-23T09:00:00Z", conclusion="FAILURE")
    with pytest.raises(ValueError, match=f"concluded 'FAILURE' on {MERGE_GROUP_SHA}"):
        _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)


def test_a_queued_candidate_is_refused_without_a_queue_commit_run(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """The pre-queue head's green run says nothing about the integrated commit."""
    _as_merge_group(_approved_after_green_head(snapshot))
    with pytest.raises(ValueError, match=f"no 'windows-store-lock' check run on {MERGE_GROUP_SHA}"):
        _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)


def test_ordering_inside_the_queue_is_still_judged_on_the_head(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """A green queue commit does not excuse an approval that preceded the head's run."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:10:00Z")
    _as_merge_group(snapshot)
    _with_queue_run(snapshot, completed_at="2026-08-23T09:00:00Z")
    with pytest.raises(ValueError, match="approval preceded platform evidence"):
        _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)


def test_a_snapshot_for_the_wrong_platform_commit_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Checks read from one commit cannot be attributed to another."""
    _approved_after_green_head(snapshot)
    with pytest.raises(ValueError, match=f"is not '{MERGE_GROUP_SHA}'"):
        _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)


# Codex review 3988684695: a rename's source path is a touched path.


def test_renaming_a_sensitive_file_away_still_triggers_the_gate(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Moving store/lock.py to a non-matching name must not skip the ordering rule."""
    renamed = {
        "filename": "research_system/storage_helpers.py",
        "previous_filename": "research_system/store/lock.py",
        "status": "renamed",
    }
    _with_files(snapshot, [renamed])
    with pytest.raises(ValueError, match="platform-sensitive paths changed: research_system/store/lock.py"):
        _platform_order(snapshot, config)


def test_adding_the_same_non_matching_file_is_not_subject_to_the_gate(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Positive control: the destination alone does not match, so the source is what triggers."""
    _with_files(snapshot, [{"filename": "research_system/storage_helpers.py", "previous_filename": None}])
    assert "not applicable" in _platform_order(snapshot, config)


def test_a_truncated_file_listing_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """A listing shorter than GitHub's own count could be hiding the sensitive file."""
    _pull_request(snapshot)["changedFiles"] = len(snapshot["restFiles"]) + 1
    with pytest.raises(ValueError, match="listing is incomplete"):
        _platform_order(snapshot, config)


def test_a_snapshot_without_the_rest_listing_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Without the REST listing, rename sources are unknown, so nothing is known."""
    del snapshot["restFiles"]
    with pytest.raises(ValueError, match="no restFiles list"):
        _platform_order(snapshot, config)


# Codex review 3988684703: platform evidence must come from the trusted producer.


@pytest.mark.parametrize(
    "suite",
    [
        {"app": {"slug": "github-actions"}, "workflowRun": {"file": {"path": ".github/workflows/lookalike.yml"}}},
        {"app": {"slug": "some-other-app"}, "workflowRun": {"file": {"path": ".github/workflows/ci.yml"}}},
        {},
    ],
    ids=["other-workflow", "other-app", "no-producer-identity"],
)
def test_a_same_named_check_from_an_untrusted_producer_is_refused(
    snapshot: dict[str, Any], config: dict[str, Any], suite: dict[str, Any]
) -> None:
    """A check run's name is chosen by whoever publishes it; only its producer is evidence."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z", suite=suite)
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    with pytest.raises(ValueError, match="refusing untrusted platform evidence"):
        _platform_order(snapshot, config)


def test_a_candidate_that_edits_the_producer_workflow_is_refused(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """A pull_request run executes the candidate's copy of ci.yml, so its green run is self-certified."""
    rows = [
        {"filename": "research_system/store/lock.py", "previous_filename": None, "status": "modified"},
        {"filename": ".github/workflows/ci.yml", "previous_filename": None, "status": "modified"},
    ]
    _with_files(_approved_after_green_head(snapshot), rows)
    with pytest.raises(ValueError, match="which produces its own platform evidence"):
        _platform_order(snapshot, config)


def test_the_same_candidate_without_the_workflow_edit_is_admitted(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Positive control: the refusal above is caused by the workflow edit alone."""
    rows = [{"filename": "research_system/store/lock.py", "previous_filename": None, "status": "modified"}]
    _with_files(_approved_after_green_head(snapshot), rows)
    assert "green before approval" in _platform_order(snapshot, config)


# Codex review 3990012209: a re-run leaves every attempt on the commit; only the latest attempt counts.


def test_a_green_rerun_supersedes_an_earlier_failed_attempt(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The normal remedy for a flaky failure -- re-run it -- must be able to admit."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:20:00Z", conclusion="FAILURE", database_id=100)
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z", database_id=200)
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    assert "green before approval" in _platform_order(snapshot, config)


def test_a_failed_rerun_supersedes_an_earlier_green_attempt(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Negative control: the older success does not survive a newer failure."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:20:00Z", database_id=100)
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z", conclusion="FAILURE", database_id=200)
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    with pytest.raises(ValueError, match="concluded 'FAILURE'"):
        _platform_order(snapshot, config)


def test_a_rerun_in_progress_keeps_the_gate_waiting(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """A newer attempt still running means the older result is no longer the answer."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:20:00Z", database_id=100)
    _with_head_run(snapshot, completed_at=None, conclusion=None, status="IN_PROGRESS", database_id=200)
    assert _platform_status(snapshot, config) == "pending"


def test_a_trusted_run_without_a_database_id_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Without an id, attempts cannot be ordered, so none can be trusted as current."""
    _approved_after_green_head(snapshot)
    del _head_rollup(snapshot)[-1]["databaseId"]
    with pytest.raises(ValueError, match="carries no databaseId"):
        _platform_order(snapshot, config)


def test_a_missing_workflow_run_points_at_the_token_permission(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Codex review 3990012219: a token without actions:read sees workflowRun as null; say so."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z", suite={"app": {"slug": "github-actions"}})
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    with pytest.raises(ValueError, match="actions: read"):
        _platform_order(snapshot, config)


# Codex review 3962013214: a still-running platform lane is a reason to wait, not to fail.


def test_platform_status_is_pending_before_the_platform_lane_registers(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """PR #262's candidate has sensitive paths and no platform run: wait, do not decide."""
    assert _platform_status(snapshot, config) == "pending"


def test_platform_status_is_pending_while_the_platform_lane_runs(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """An in-progress run is not terminal evidence in either direction."""
    _with_head_run(snapshot, completed_at=None, conclusion=None, status="IN_PROGRESS")
    assert _platform_status(snapshot, config) == "pending"


def test_platform_status_is_ready_once_the_platform_lane_completes(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Completion ends the wait even on failure; the gate then decides."""
    _with_head_run(snapshot, completed_at="2026-08-23T07:30:00Z", conclusion="FAILURE")
    assert _platform_status(snapshot, config) == "ready"


def test_platform_status_waits_for_the_queue_commit_too(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Inside a queue, a finished head run is not enough to decide."""
    _as_merge_group(_approved_after_green_head(snapshot))
    _with_queue_run(snapshot, completed_at=None, conclusion=None, status="IN_PROGRESS")
    assert _platform_status(snapshot, config, platform=MERGE_GROUP_SHA) == "pending"


def test_platform_status_never_waits_on_untouched_surfaces(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Only the candidates the ordering rule governs spend runner time waiting."""
    _with_files(snapshot, DOCS_ONLY)
    assert _platform_status(snapshot, config) == "not-applicable"


def test_an_in_progress_platform_lane_still_blocks_the_gate_itself(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """If the wait budget runs out, the gate fails closed rather than passing."""
    _with_head_run(snapshot, completed_at=None, conclusion=None, status="IN_PROGRESS")
    with pytest.raises(ValueError, match="'IN_PROGRESS'"):
        _platform_order(snapshot, config)


# Codex review 3988684692: a review change on a queued pull request removes it from the queue.


def _queue_snapshot(entry: dict[str, Any] | None) -> dict[str, Any]:
    """Return the minimal payload the dequeue step queries."""
    return {"data": {"repository": {"pullRequest": {"id": "PR_node", "mergeQueueEntry": entry}}}}


@pytest.mark.parametrize("event_name", ["pull_request_review", "pull_request_review_comment"])
def test_a_review_change_on_a_queued_pull_request_dequeues_it(event_name: str) -> None:
    """The queue commit's green check cannot see this change, so the entry must go."""
    assert queue_disposition(_queue_snapshot({"id": "MQE_1", "state": "QUEUED"}), event_name=event_name) == "dequeue"


def test_a_review_change_on_an_unqueued_pull_request_keeps_it(snapshot: dict[str, Any]) -> None:
    """Positive control on real evidence: PR #262's snapshot records no queue entry."""
    assert queue_disposition(snapshot, event_name="pull_request_review_comment") == "keep"


def test_a_push_to_a_queued_pull_request_does_not_dequeue_from_this_step() -> None:
    """Only review events are this step's business; a push already rebuilds the queue."""
    assert queue_disposition(_queue_snapshot({"id": "MQE_1", "state": "QUEUED"}), event_name="pull_request") == "keep"


def test_unknown_queue_membership_is_refused() -> None:
    """A snapshot that did not ask about the queue cannot say the pull request is not in it."""
    with pytest.raises(ValueError, match="queue membership is unknown"):
        queue_disposition(
            {"data": {"repository": {"pullRequest": {"id": "PR_node"}}}}, event_name="pull_request_review"
        )


# Codex review 3988684699: one evaluation certifies one merge-queue entry.


def _compare(total: int, merge_base: str = MERGE_GROUP_BASE) -> dict[str, Any]:
    """Return a REST compare response for base...merge-group head."""
    return {"merge_base_commit": {"sha": merge_base}, "total_commits": total}


def test_a_single_entry_merge_group_is_admitted(config: dict[str, Any]) -> None:
    """Positive control: the ruleset's one-entry group passes."""
    verdict = evaluate_merge_group_size(
        _compare(1),
        base_sha=MERGE_GROUP_BASE,
        head_sha=MERGE_GROUP_SHA,
        max_entries=config["merge_queue"]["max_entries"],
    )
    assert "1 entry" in verdict


def test_a_batched_merge_group_is_refused(config: dict[str, Any]) -> None:
    """Two entries would certify the second pull request on the first one's evidence."""
    with pytest.raises(ValueError, match="carries 2 entries"):
        evaluate_merge_group_size(
            _compare(2),
            base_sha=MERGE_GROUP_BASE,
            head_sha=MERGE_GROUP_SHA,
            max_entries=config["merge_queue"]["max_entries"],
        )


@pytest.mark.parametrize(
    ("compare", "message"),
    [
        (_compare(1, merge_base="0" * 40), "is not built on base"),
        (_compare(0), "reports no commits"),
        ({"merge_base_commit": {"sha": MERGE_GROUP_BASE}}, "reports no commits"),
    ],
    ids=["foreign-base", "empty", "no-count"],
)
def test_an_uncountable_merge_group_is_refused(compare: dict[str, Any], message: str) -> None:
    """If the entries cannot be counted from the base, the group is not admissible."""
    with pytest.raises(ValueError, match=message):
        evaluate_merge_group_size(compare, base_sha=MERGE_GROUP_BASE, head_sha=MERGE_GROUP_SHA, max_entries=1)


def test_admission_group_limit_matches_the_one_pull_request_it_evaluates(config: dict[str, Any]) -> None:
    """Raising the limit would need admission to evaluate every entry; it does not."""
    assert config["merge_queue"]["max_entries"] == 1


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("research_system/store/lock.py", True),
        ("research_system/evals/release_publication.py", True),
        ("research_system/authority.py", True),
        ("research_system/store/nested/deep.py", True),
        ("shared/durability.py", True),
        ("papers/P01/draft.md", False),
        ("research_system/context/compiler.py", False),
    ],
)
def test_sensitive_path_matching(path: str, expected: bool, config: dict[str, Any]) -> None:
    """The configured patterns select filesystem/concurrency code and no more."""
    assert path_is_sensitive(path, config["platform_order"]["sensitive_paths"]) is expected


# --------------------------------------------------------------------------
# Wiring: a gate that is written but not invoked is not a gate.
# --------------------------------------------------------------------------


def test_cli_blocks_on_the_recorded_candidate(tmp_path: Path, snapshot: dict[str, Any]) -> None:
    """The command-line entry point returns non-zero for the blocked candidate."""
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    argv = [
        "thread-finality",
        "--snapshot",
        str(snapshot_path),
        "--candidate-sha",
        PR262_CANDIDATE,
        "--config",
        str(CONFIG_PATH),
    ]
    assert main(argv) == 1


def test_workflow_reevaluates_on_every_admission_relevant_event() -> None:
    """Both gates run, and a newly published thread retriggers the evaluation."""
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    # PyYAML parses the unquoted `on:` key as the boolean True.
    triggers = workflow.get("on", workflow.get(True))
    assert triggers is not None, "workflow must declare triggers"
    for event in ("pull_request", "pull_request_review", "pull_request_review_comment", "merge_group"):
        assert event in triggers, f"merge admission must re-evaluate on {event}"
    # A newly published thread arrives as a review comment; there is no
    # `pull_request_review_thread` Actions trigger to key on.
    assert "created" in triggers["pull_request_review_comment"]["types"]
    assert "submitted" in triggers["pull_request_review"]["types"]

    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "tools/check_merge_admission.py thread-finality" in body
    assert "tools/check_merge_admission.py platform-order" in body


def _target_step_script() -> str:
    """Return the shell script of the step that resolves the PR and platform commit."""
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["merge-admission"]["steps"]
    matches = [step for step in steps if step.get("id") == "target"]
    assert len(matches) == 1, "workflow must have exactly one step with id 'target'"
    return matches[0]["run"]


def test_manual_dispatch_is_bound_to_the_sha_its_check_lands_on() -> None:
    """Codex review 3962013254: a dispatch may not attach evidence for another commit."""
    script = _target_step_script()
    dispatch_branch = script.split("workflow_dispatch)", 1)[1].split(";;", 1)[0]
    assert 'expected="$RUN_SHA"' in dispatch_branch
    assert 'platform="$RUN_SHA"' in dispatch_branch


def test_merge_group_platform_evidence_comes_from_the_queue_commit() -> None:
    """Codex review 3962013225: the queue commit, not the PR head, carries platform evidence."""
    script = _target_step_script()
    merge_group_branch = script.split("merge_group)", 1)[1].split(";;", 1)[0]
    assert 'platform="$MERGE_GROUP_HEAD_SHA"' in merge_group_branch
    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert '--platform-sha "${{ steps.target.outputs.platform }}"' in body


def test_workflow_waits_for_a_pending_platform_lane_before_deciding() -> None:
    """Codex review 3962013214: a running platform lane is polled, not failed on sight."""
    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "tools/check_merge_admission.py platform-status" in body
    assert 'while [ "$(status_of)" = "pending" ]' in body


def _steps() -> list[dict[str, Any]]:
    """Return the admission job's steps."""
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return workflow["jobs"]["merge-admission"]["steps"]


def test_review_events_dequeue_a_queued_pull_request() -> None:
    """Codex review 3988684692: the dequeue step exists, runs on both review events, and calls the mutation."""
    matches = [step for step in _steps() if "queue-disposition" in step.get("run", "")]
    assert len(matches) == 1, "exactly one step must decide queue disposition"
    step = matches[0]
    assert "pull_request_review'" in step["if"] and "pull_request_review_comment'" in step["if"]
    assert "dequeuePullRequest" in step["run"]


def test_merge_group_runs_count_their_entries() -> None:
    """Codex review 3988684699: queue commits are sized before admission trusts one PR's evidence."""
    matches = [step for step in _steps() if "merge-group-size" in step.get("run", "")]
    assert len(matches) == 1
    assert matches[0]["if"] == "github.event_name == 'merge_group'"


def test_snapshot_carries_rename_sources_and_producer_identity() -> None:
    """Codex reviews 3988684695 and 3988684703: the evidence the tool now requires is actually captured."""
    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pulls/${PR_NUMBER}/files" in body and "previous_filename" in body
    assert "changedFiles" in body
    assert "checkSuite{ app{slug} workflowRun{ file{path} } }" in body


def test_admission_and_sweep_jobs_can_read_workflow_run_identity() -> None:
    """Codex review 3990012219: job-level permissions zero every unlisted scope, including actions."""
    admission = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))["jobs"]["merge-admission"]
    sweep = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "merge-admission-sweep.yml").read_text(encoding="utf-8")
    )["jobs"]["sweep"]
    assert admission["permissions"].get("actions") in {"read", "write"}
    assert sweep["permissions"].get("actions") in {"read", "write"}
    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        "databaseId name status conclusion startedAt completedAt" in body
    ), "attempts cannot be ordered without databaseId"


def test_python_captures_strip_carriage_returns_on_windows() -> None:
    """Python on Windows ends lines with CRLF; an unstripped capture silently breaks SHA comparisons."""
    captures = 0
    for step in _steps():
        script = step.get("run", "").replace("\\\n", " ")
        for line in script.splitlines():
            if "$(python" in line:
                captures += 1
                assert "tr -d '\\r'" in line, f"step {step.get('name')!r} captures python output without stripping CR"
    assert captures >= 3, "expected the candidate, disposition, and PR-id captures"


# Codex review 3988790015: reopening a thread emits no event, so a schedule re-derives thread state.

SWEEP_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "merge-admission-sweep.yml"
GATE_RUN_ID = 34594304981


def _sweep_gate(config: dict[str, Any]) -> SweepGate:
    """Return the configured admission check the sweep re-runs."""
    section = config["sweep"]
    return SweepGate(check_run=section["gate_check_run"], workflow_path=section["gate_workflow_path"])


def _open_pull_request(
    *,
    live: int = 1,
    outdated: int = 0,
    queued: bool = False,
    conclusion: str | None = "SUCCESS",
    status: str = "COMPLETED",
    workflow_path: str = ".github/workflows/merge-admission.yml",
) -> dict[str, Any]:
    """Return one open pull request as the sweep query reports it."""
    threads = (
        [{"isResolved": False, "isOutdated": False} for _ in range(live)]
        + [{"isResolved": False, "isOutdated": True} for _ in range(outdated)]
        + [{"isResolved": True, "isOutdated": False}]
    )
    gate = {
        "__typename": "CheckRun",
        "databaseId": 500,
        "name": "merge-admission",
        "status": status,
        "conclusion": conclusion,
        "checkSuite": {"workflowRun": {"databaseId": GATE_RUN_ID, "file": {"path": workflow_path}}},
    }
    rollup = {"contexts": {"pageInfo": {"hasNextPage": False}, "nodes": [gate]}}
    return {
        "number": 278,
        "id": "PR_278",
        "mergeQueueEntry": {"id": "MQE_278"} if queued else None,
        "reviewThreads": {"pageInfo": {"hasNextPage": False}, "nodes": threads},
        "commits": {
            "pageInfo": {"hasNextPage": False},
            "nodes": [{"commit": {"oid": "a" * 40, "statusCheckRollup": rollup}}],
        },
    }


def _sweep_payload(*pulls: dict[str, Any], truncated: bool = False) -> dict[str, Any]:
    """Return the sweep query response wrapping the given pull requests."""
    return {"data": {"repository": {"pullRequests": {"pageInfo": {"hasNextPage": truncated}, "nodes": list(pulls)}}}}


PRODUCERS = ["chatgpt-codex-connector"]
GATE_STARTED_AT = "2026-09-25T16:58:00Z"
GATE_FAILED_AT = "2026-09-25T17:00:00Z"


def _failed_then_reacted(
    plus_one_at: str | None, login: str = CODEX_BOT, comment: tuple[str, str] | None = None
) -> dict[str, Any]:
    """An open PR, no live thread, whose admission run started at GATE_STARTED_AT and failed at GATE_FAILED_AT.

    ``plus_one_at`` adds a +1 by ``login``; ``comment`` adds a producer comment (createdAt, body).
    """
    pull_request = _open_pull_request(live=0, conclusion="FAILURE")
    gate = pull_request["commits"]["nodes"][0]["commit"]["statusCheckRollup"]["contexts"]["nodes"][0]
    gate["startedAt"] = GATE_STARTED_AT
    gate["completedAt"] = GATE_FAILED_AT
    nodes = (
        [] if plus_one_at is None else [{"content": "THUMBS_UP", "createdAt": plus_one_at, "user": {"login": login}}]
    )
    pull_request["reactions"] = {"pageInfo": {"hasNextPage": False}, "nodes": nodes}
    comments = [] if comment is None else [{"createdAt": comment[0], "body": comment[1], "author": {"login": login}}]
    pull_request["comments"] = {"nodes": comments}
    return pull_request


@pytest.mark.parametrize("plus_one_at", ["2026-09-25T17:05:00Z", "2026-09-25T16:59:00Z"], ids=["after", "during"])
def test_a_plus_one_after_a_failed_admission_started_re_runs_it(config: dict[str, Any], plus_one_at: str) -> None:
    """Reactions trigger no workflow. A +1 that landed while the run was still evaluating was not in its snapshot."""
    listing = _sweep_payload(_failed_then_reacted(plus_one_at))
    assert sweep_actions(listing, gate=_sweep_gate(config), producers=PRODUCERS) == [f"rerun {GATE_RUN_ID} 278"]


def test_a_quota_reply_after_a_failed_admission_re_runs_it(config: dict[str, Any]) -> None:
    """The quota reply is an issue comment, which triggers nothing; without a re-run its remedy never appears."""
    pull_request = _failed_then_reacted(None, comment=("2026-09-25T17:05:00Z", QUOTA_BODY))
    assert sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config), producers=PRODUCERS) == [
        f"rerun {GATE_RUN_ID} 278"
    ]


@pytest.mark.parametrize(
    ("plus_one_at", "login"),
    [(None, CODEX_BOT), ("2026-09-25T16:55:00Z", CODEX_BOT), ("2026-09-25T17:05:00Z", "stephendor")],
    ids=["no-plus-one", "plus-one-before-the-run", "someone-elses-plus-one"],
)
def test_the_sweep_does_not_re_run_without_a_newer_producer_signal(
    config: dict[str, Any], plus_one_at: str | None, login: str
) -> None:
    """A signal the failed run already saw, or none at all, must not pile up re-runs."""
    listing = _sweep_payload(_failed_then_reacted(plus_one_at, login, comment=("2026-09-25T17:05:00Z", "thanks")))
    assert sweep_actions(listing, gate=_sweep_gate(config), producers=PRODUCERS) == []


def test_the_sweep_snapshot_requests_reactions_comments_and_start_times() -> None:
    sweep = SWEEP_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "reactions(first:100, content:THUMBS_UP){ pageInfo{hasNextPage}" in sweep
    assert "comments(last:20){ nodes{ createdAt body author{login} } }" in sweep
    assert "conclusion startedAt completedAt" in sweep


def test_a_reopened_thread_behind_a_green_admission_check_is_re_run(config: dict[str, Any]) -> None:
    """The silent case: success stands while a thread is live again."""
    assert sweep_actions(_sweep_payload(_open_pull_request()), gate=_sweep_gate(config)) == [f"rerun {GATE_RUN_ID} 278"]


def test_a_queued_pull_request_with_a_live_thread_is_dequeued_and_re_run(config: dict[str, Any]) -> None:
    """Both the queue entry and the stale success must go."""
    actions = sweep_actions(_sweep_payload(_open_pull_request(queued=True)), gate=_sweep_gate(config))
    assert actions == ["dequeue PR_278 278", f"rerun {GATE_RUN_ID} 278"]


@pytest.mark.parametrize(
    "pull_request",
    [
        _open_pull_request(live=0, queued=True),
        _open_pull_request(live=0, outdated=1, queued=True),
    ],
    ids=["all-resolved", "only-outdated-unresolved"],
)
def test_a_pull_request_without_a_live_thread_is_left_alone(
    config: dict[str, Any], pull_request: dict[str, Any]
) -> None:
    """Positive control: a queued, green pull request with no live thread needs nothing."""
    assert sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config)) == []


@pytest.mark.parametrize(
    ("conclusion", "status"),
    [("FAILURE", "COMPLETED"), (None, "IN_PROGRESS")],
    ids=["already-failing", "already-re-running"],
)
def test_an_admission_check_that_is_not_green_is_not_re_run_again(
    config: dict[str, Any], conclusion: str | None, status: str
) -> None:
    """Repeated sweeps must not pile re-runs onto a check that already reflects the thread."""
    pull_request = _open_pull_request(conclusion=conclusion, status=status)
    assert sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config)) == []


def _with_gate_attempt(pull_request: dict[str, Any], *, database_id: int, conclusion: str, run_id: int) -> None:
    """Append another attempt of the admission check to a pull request's head rollup."""
    contexts = pull_request["commits"]["nodes"][0]["commit"]["statusCheckRollup"]["contexts"]["nodes"]
    attempt = copy.deepcopy(contexts[0])
    attempt.update({"databaseId": database_id, "conclusion": conclusion, "status": "COMPLETED"})
    attempt["checkSuite"]["workflowRun"]["databaseId"] = run_id
    contexts.append(attempt)


def test_the_sweep_ignores_an_old_success_behind_a_newer_failure(config: dict[str, Any]) -> None:
    """Codex review 3990012209: the current attempt already reflects the live thread."""
    pull_request = _open_pull_request()
    _with_gate_attempt(pull_request, database_id=600, conclusion="FAILURE", run_id=777)
    assert sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config)) == []


def test_the_sweep_re_runs_the_newer_green_attempt(config: dict[str, Any]) -> None:
    """Positive control: when the latest attempt is the green one, that run is re-run."""
    pull_request = _open_pull_request(conclusion="FAILURE")
    _with_gate_attempt(pull_request, database_id=600, conclusion="SUCCESS", run_id=777)
    assert sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config)) == ["rerun 777 278"]


def test_a_same_named_check_from_another_workflow_is_not_re_run(config: dict[str, Any]) -> None:
    """Only the configured admission workflow's run is re-run."""
    pull_request = _open_pull_request(workflow_path=".github/workflows/lookalike.yml")
    assert sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config)) == []


def test_a_truncated_pull_request_listing_is_refused(config: dict[str, Any]) -> None:
    """A sweep that saw only some open pull requests cannot report the rest as clean."""
    with pytest.raises(ValueError, match="truncated"):
        sweep_actions(_sweep_payload(_open_pull_request(), truncated=True), gate=_sweep_gate(config))


def _page(*pulls: dict[str, Any], has_next: bool) -> dict[str, Any]:
    """Return one page of a ``--paginate --slurp`` sweep listing."""
    return _sweep_payload(*pulls, truncated=has_next)


def _numbered(number: int, **kwargs: Any) -> dict[str, Any]:
    """Return an open pull request with a distinct number and node id."""
    pull_request = _open_pull_request(**kwargs)
    pull_request.update({"number": number, "id": f"PR_{number}"})
    return pull_request


def test_the_sweep_acts_on_every_page_of_open_pull_requests(config: dict[str, Any]) -> None:
    """Codex review 3990242357: a second page of pull requests is swept, not abandoned."""
    listing = [_page(_numbered(101, live=0), has_next=True), _page(_numbered(151), has_next=False)]
    assert sweep_actions(listing, gate=_sweep_gate(config)) == [f"rerun {GATE_RUN_ID} 151"]


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        ((True, True), "truncated or inconsistent"),
        ((False, False), "truncated or inconsistent"),
        ((), "contains no pages"),
    ],
    ids=["stopped-early", "page-claims-last-but-more-follow", "empty"],
)
def test_an_incomplete_or_inconsistent_page_chain_is_refused(
    config: dict[str, Any], flags: tuple[bool, ...], message: str
) -> None:
    """Pagination must not reintroduce the silent skip it replaced."""
    listing = [_page(_numbered(200 + index), has_next=flag) for index, flag in enumerate(flags)]
    with pytest.raises(ValueError, match=message):
        sweep_actions(listing, gate=_sweep_gate(config))


def test_a_pull_request_listed_on_two_pages_is_refused(config: dict[str, Any]) -> None:
    """A cursor that repeats a page is a broken listing, not two pull requests."""
    listing = [_page(_numbered(301), has_next=True), _page(_numbered(301), has_next=False)]
    with pytest.raises(ValueError, match="more than one page"):
        sweep_actions(listing, gate=_sweep_gate(config))


def test_the_sweep_cli_accepts_a_slurped_page_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The workflow passes the --slurp array straight through."""
    listing = [_page(_numbered(401, live=0), has_next=True), _page(_numbered(451, queued=True), has_next=False)]
    snapshot_path = tmp_path / "sweep.json"
    snapshot_path.write_text(json.dumps(listing), encoding="utf-8")
    assert main(["sweep", "--snapshot", str(snapshot_path), "--config", str(CONFIG_PATH)]) == 0
    assert capsys.readouterr().out.splitlines() == ["dequeue PR_451 451", f"rerun {GATE_RUN_ID} 451"]


def test_truncated_threads_are_refused(config: dict[str, Any]) -> None:
    """The live thread could be on the page the sweep did not read."""
    pull_request = _open_pull_request(live=0)
    pull_request["reviewThreads"]["pageInfo"]["hasNextPage"] = True
    with pytest.raises(ValueError, match="truncated"):
        sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config))


def test_a_sweep_without_queue_membership_is_refused(config: dict[str, Any]) -> None:
    """A query that did not ask about the queue cannot say the pull request is not queued."""
    pull_request = _open_pull_request()
    del pull_request["mergeQueueEntry"]
    with pytest.raises(ValueError, match="queue membership is unknown"):
        sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config))


def test_the_sweep_cli_prints_one_action_per_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], config: dict[str, Any]
) -> None:
    """The workflow reads the CLI's stdout line by line."""
    snapshot_path = tmp_path / "sweep.json"
    snapshot_path.write_text(json.dumps(_sweep_payload(_open_pull_request(queued=True))), encoding="utf-8")
    assert main(["sweep", "--snapshot", str(snapshot_path), "--config", str(CONFIG_PATH)]) == 0
    assert capsys.readouterr().out.splitlines() == ["dequeue PR_278 278", f"rerun {GATE_RUN_ID} 278"]


def test_the_sweep_cli_prints_nothing_when_there_is_nothing_to_do(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty line would make the workflow's non-empty-file check treat 'no work' as a blank action."""
    snapshot_path = tmp_path / "sweep.json"
    snapshot_path.write_text(json.dumps(_sweep_payload(_open_pull_request(live=0))), encoding="utf-8")
    assert main(["sweep", "--snapshot", str(snapshot_path), "--config", str(CONFIG_PATH)]) == 0
    assert capsys.readouterr().out == ""


def test_the_sweep_targets_the_real_admission_job(config: dict[str, Any]) -> None:
    """The configured check name and workflow must name the job that actually reports admission."""
    gate = _sweep_gate(config)
    assert (REPO_ROOT / gate.workflow_path).resolve() == WORKFLOW_PATH.resolve()
    assert gate.check_run in yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))["jobs"]


def test_the_sweep_workflow_runs_on_a_schedule_and_acts() -> None:
    """A sweep that is written but not scheduled, or never acts, is not a mechanism."""
    workflow = yaml.load(SWEEP_WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert workflow["on"]["schedule"] == [{"cron": "*/5 * * * *"}]
    body = SWEEP_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "tools/check_merge_admission.py sweep" in body
    assert "gh api graphql --paginate --slurp" in body
    assert "after:$endCursor" in body and "pageInfo{hasNextPage endCursor}" in body
    assert "dequeuePullRequest" in body
    assert 'gh run rerun "$target"' in body
    assert "databaseId file{path}" in body


def _bash() -> str:
    """Resolve Git's bash rather than the WSL launcher stub, failing if none exists."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found or "system32" in found.lower():
        pytest.fail("no usable bash: the workflow scripts cannot be syntax-checked, and must not silently skip")
    return found


WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOW_FILES = sorted(WORKFLOW_DIR.glob("*.yml"))
WATCHDOG_WORKFLOW_PATH = WORKFLOW_DIR / "ars-artefact-currency-watchdog.yml"


def _declared_shell(block: Any) -> str | None:
    """Return ``defaults.run.shell`` from a workflow or job mapping, if it declares one."""
    if not isinstance(block, dict):
        return None
    run = block.get("defaults", {}).get("run", {})
    return run.get("shell") if isinstance(run, dict) else None


def _bash_scripts(workflow_path: Path) -> list[tuple[str, str]]:
    """Return (label, script) for every step that runs under bash: a step, job or workflow default says so.

    Steps under the Windows default shell are PowerShell, which `bash -n` would misread, so they are left out.
    """
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow_shell = _declared_shell(workflow)
    scripts: list[tuple[str, str]] = []
    for job_name, job in workflow["jobs"].items():
        job_shell = _declared_shell(job) or workflow_shell
        for step in job.get("steps", []):
            if "run" in step and (step.get("shell") or job_shell) == "bash":
                scripts.append((f"{job_name} / {step.get('name')}", step["run"]))
    return scripts


@pytest.mark.parametrize("workflow_path", WORKFLOW_FILES, ids=lambda path: path.name)
def test_every_workflow_run_script_is_valid_bash(workflow_path: Path) -> None:
    """The scripts are only ever executed on GitHub, so nothing local noticed a quoting break.

    An apostrophe in a comment inside the single-quoted GraphQL query ended the string early, and
    every admission run died with a bash syntax error (found 2026-09-30 by re-running the check on
    PR #304). String assertions on the YAML cannot see that; `bash -n` on each script can. It runs on
    every workflow, not only the two admission ones: the same break is possible in any of them.
    """
    for name, script in _bash_scripts(workflow_path):
        rendered = re.sub(r"\$\{\{.*?\}\}", "EXPR", script)
        result = subprocess.run([_bash(), "-n"], input=rendered, capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, f"{workflow_path.name} step {name!r} is not valid bash: {result.stderr}"


def test_the_bash_syntax_check_is_not_vacuous() -> None:
    """A discovery or shell-resolution slip would leave the parametrized check above passing over nothing."""
    names = {path.name for path in WORKFLOW_FILES}
    for expected in (
        "merge-admission.yml",
        "merge-admission-sweep.yml",
        "ars-artefact-currency.yml",
        "ars-artefact-currency-watchdog.yml",
        "ci.yml",
    ):
        assert expected in names, f"{expected} is missing from the workflow set"
        assert _bash_scripts(WORKFLOW_DIR / expected), f"{expected} contributes no bash script to the syntax check"


def test_a_broken_bash_script_is_caught_by_the_syntax_check() -> None:
    """Watched failure: the #304 break, an apostrophe inside a single-quoted string, must fail `bash -n`."""
    broken = "gh api graphql -f query='\n  # Codex's reply\n  query { x }'\n"
    result = subprocess.run([_bash(), "-n"], input=broken, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode != 0


# Campaign M of the 2026-09-29 system review: the sweep's `*/5` cron fired about every four hours, and
# nothing measured it (obs 2026-09-29-sweep-cron-runs-at-two-percent-of-its-stated-cadence).

SWEEP_RUNS_FIXTURE = Path(__file__).parent / "fixtures" / "merge_admission_sweep_runs_2026-10-02.json"
GIT_INSTRUCTIONS_PATH = REPO_ROOT / ".claude" / "instructions" / "git.instructions.md"
CADENCE_NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
BOUND_MINUTES = int(SWEEP_MAX_RUN_AGE.total_seconds() // 60)


def _minutes_ago(minutes: float) -> str:
    return (CADENCE_NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sweep_run(
    minutes_ago: float, *, status: str = "completed", conclusion: str | None = "success", event: str = "schedule"
) -> dict[str, Any]:
    """One row of the REST workflow-runs listing the watchdog reads, created ``minutes_ago`` before CADENCE_NOW."""
    return {"created_at": _minutes_ago(minutes_ago), "event": event, "status": status, "conclusion": conclusion}


def _run_list(*runs: dict[str, Any]) -> dict[str, Any]:
    return {"workflow_runs": list(runs)}


def _recorded_sweep_runs() -> dict[str, Any]:
    """The real run list of the sweep as captured on 2026-10-02 (every run on record)."""
    return json.loads(SWEEP_RUNS_FIXTURE.read_text(encoding="utf-8"))


def _recorded_times(recorded: dict[str, Any]) -> list[datetime]:
    return sorted(datetime.fromisoformat(row["created_at"]) for row in recorded["workflow_runs"])


def _recorded_gaps_minutes(recorded: dict[str, Any]) -> list[float]:
    times = _recorded_times(recorded)
    return [(later - earlier).total_seconds() / 60 for earlier, later in zip(times, times[1:], strict=False)]


def test_a_sweep_whose_newest_successful_run_is_older_than_the_bound_is_refused() -> None:
    """Watched failure: the real defect was a schedule that stopped arriving while every run that did arrive was green."""
    age = BOUND_MINUTES + 60
    listing = _run_list(_sweep_run(age), _sweep_run(age + 240))
    with pytest.raises(ValueError, match=rf"{age} min old, over the {BOUND_MINUTES}-minute bound"):
        evaluate_sweep_cadence(listing, now=CADENCE_NOW)


def test_a_fresh_sweep_run_passes_and_reports_the_measured_gap() -> None:
    """Positive control: the same evaluator passes a fresh list and names the numbers it measured."""
    verdict = evaluate_sweep_cadence(_run_list(_sweep_run(42), _sweep_run(300)), now=CADENCE_NOW)
    assert "42 min old" in verdict
    assert f"bound {BOUND_MINUTES} min" in verdict
    assert "largest gap between successful runs 258 min" in verdict
    assert "2 runs examined" in verdict


@pytest.mark.parametrize(
    ("age", "refused"),
    [(BOUND_MINUTES - 1, False), (BOUND_MINUTES, False), (BOUND_MINUTES + 1, True)],
    ids=["inside", "exactly-at", "one-minute-over"],
)
def test_the_bound_refuses_only_what_is_older_than_it(age: int, refused: bool) -> None:
    """The bound is `older than`, so a run exactly at it stands and one minute more does not."""
    listing = _run_list(_sweep_run(age))
    if refused:
        with pytest.raises(ValueError, match="bound"):
            evaluate_sweep_cadence(listing, now=CADENCE_NOW)
    else:
        assert f"{age} min old" in evaluate_sweep_cadence(listing, now=CADENCE_NOW)


@pytest.mark.parametrize(
    ("status", "conclusion"),
    [("completed", "failure"), ("completed", "cancelled"), ("in_progress", None), ("queued", None)],
)
def test_a_fresh_run_that_did_not_succeed_does_not_satisfy_the_bound(status: str, conclusion: str | None) -> None:
    """A sweep that fires and fails protects nothing, and the refusal names the newest run's real state."""
    listing = _run_list(_sweep_run(5, status=status, conclusion=conclusion), _sweep_run(BOUND_MINUTES + 120))
    with pytest.raises(ValueError, match=rf"newest run of any outcome .* \({status}/{conclusion or 'none'}\)"):
        evaluate_sweep_cadence(listing, now=CADENCE_NOW)


@pytest.mark.parametrize(
    "listing",
    [_run_list(), _run_list(_sweep_run(10, conclusion="failure"))],
    ids=["no-runs", "only-failures"],
)
def test_a_run_list_with_no_successful_run_is_refused(listing: dict[str, Any]) -> None:
    """Silent absence: a sweep that never ran must not read as a sweep that ran recently."""
    with pytest.raises(ValueError, match="no successful"):
        evaluate_sweep_cadence(listing, now=CADENCE_NOW)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "JSON object"),
        ({}, "workflow_runs"),
        ({"workflow_runs": "none"}, "workflow_runs"),
        ({"workflow_runs": [1]}, "workflow_runs"),
        ({"workflow_runs": [{"status": "completed", "conclusion": "success"}]}, "created_at"),
        ({"workflow_runs": [{**_sweep_run(10), "created_at": "2026-10-02T11:00:00"}]}, "timezone"),
        ({"workflow_runs": [{**_sweep_run(10), "created_at": "yesterday"}]}, "ISO-8601"),
    ],
    ids=["list", "no-key", "not-a-list", "not-an-object", "no-timestamp", "naive-timestamp", "garbage-timestamp"],
)
def test_a_malformed_run_list_is_refused(payload: Any, message: str) -> None:
    """Every gate here fails closed on evidence it cannot read, rather than passing on a guess."""
    with pytest.raises(ValueError, match=message):
        evaluate_sweep_cadence(payload, now=CADENCE_NOW)


def test_the_largest_gap_between_runs_is_reported_so_the_bound_can_be_tuned() -> None:
    """The gap that matters for choosing the bound is the longest the platform has produced, not the newest age."""
    listing = _run_list(_sweep_run(30), _sweep_run(30 + 420), _sweep_run(30 + 420 + 100))
    assert "largest gap between successful runs 420 min" in evaluate_sweep_cadence(listing, now=CADENCE_NOW)


def test_a_single_clock_skewed_run_does_not_trip_the_watchdog() -> None:
    """A run stamped a few seconds after the runner's clock is fresh, not an error."""
    listing = _run_list(_sweep_run(-0.1))
    assert "0 min old" in evaluate_sweep_cadence(listing, now=CADENCE_NOW)


def test_the_recorded_real_sweep_passes_at_capture_and_fails_once_the_bound_has_elapsed() -> None:
    """Real evidence both ways: the sweep as it ran passes, and the same run list a bound later does not."""
    recorded = _recorded_sweep_runs()
    captured = datetime.fromisoformat(recorded["captured_at"])
    newest = _recorded_times(recorded)[-1]
    expected_age = int((captured - newest).total_seconds() // 60)
    assert f"{expected_age} min old" in evaluate_sweep_cadence(recorded, now=captured)
    with pytest.raises(ValueError, match="bound"):
        evaluate_sweep_cadence(recorded, now=newest + SWEEP_MAX_RUN_AGE + timedelta(minutes=1))


def test_the_default_bound_clears_the_longest_gap_on_record() -> None:
    """A bound under the platform's normal throttling would alarm on a healthy sweep."""
    assert max(_recorded_gaps_minutes(_recorded_sweep_runs())) < BOUND_MINUTES


def test_the_cadence_cli_refuses_a_stale_run_list_and_prints_the_gap_for_a_fresh_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The workflow's only interface is this command's exit status and its stdout."""
    stale = tmp_path / "stale.json"
    stale.write_text(json.dumps(_run_list(_sweep_run(BOUND_MINUTES + 30))), encoding="utf-8")
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(_run_list(_sweep_run(7))), encoding="utf-8")
    common = ["--now", CADENCE_NOW.isoformat(), "--config", str(CONFIG_PATH)]

    assert main(["sweep-cadence", "--runs", str(stale), *common]) == 1
    assert f"{BOUND_MINUTES + 30} min old" in capsys.readouterr().err

    assert main(["sweep-cadence", "--runs", str(fresh), *common]) == 0
    assert "7 min old" in capsys.readouterr().out

    assert main(["sweep-cadence", *common]) == 1
    assert "--runs is required" in capsys.readouterr().err


def _workflow_document(path: Path) -> dict[str, Any]:
    """Load a workflow without YAML 1.1 coercing the `on` key."""
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_the_cadence_watchdog_is_not_cron_only_and_cannot_be_skipped() -> None:
    """It lives in a workflow that also fires on events, which the platform does not throttle like a cron.

    A cron-only watchdog would be delayed by the behaviour it measures. The job is also not conditional:
    a watchdog that can be skipped, or that continues on error, reads green while checking nothing.
    """
    workflow = _workflow_document(WATCHDOG_WORKFLOW_PATH)
    assert "schedule" in workflow["on"]
    assert {"push", "pull_request", "merge_group"} <= set(workflow["on"])
    job = workflow["jobs"]["sweep-cadence"]
    assert job["runs-on"].startswith("windows")
    assert "if" not in job and "continue-on-error" not in job
    assert all("if" not in step and "continue-on-error" not in step for step in job["steps"])


def test_the_cadence_watchdog_reads_the_sweeps_runs_and_runs_the_checker() -> None:
    job = _workflow_document(WATCHDOG_WORKFLOW_PATH)["jobs"]["sweep-cadence"]
    scripts = {step["name"]: step["run"] for step in job["steps"] if "run" in step}
    assert (WORKFLOW_DIR / "merge-admission-sweep.yml").is_file()
    reader = next(script for script in scripts.values() if "actions/workflows/" in script)
    assert "actions/workflows/merge-admission-sweep.yml/runs" in reader
    checker = next(script for script in scripts.values() if "sweep-cadence" in script)
    assert "tools/check_merge_admission.py sweep-cadence --runs sweep-runs.json" in checker
    # `tee` would otherwise report its own success for a failing checker.
    assert "set -euo pipefail" in checker


def _header_text(path: Path) -> str:
    """The comment block before a workflow's `on:` key, markers removed and whitespace collapsed."""
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("on:"):
            break
        if line.startswith("#"):
            lines.append(line.lstrip("#").strip())
    return re.sub(r"\s+", " ", " ".join(lines))


def test_the_sweep_header_states_the_measured_window_not_the_intended_one() -> None:
    """The header is a claim about the gate's exposure. It must carry the measured figures, and they must be true.

    The original header promised an exposure window of 5-10 minutes on the strength of a `*/5` schedule
    that fired about every four hours. This recomputes every figure the header cites from the committed
    run list, so the header cannot drift from the evidence it names.
    """
    header = _header_text(SWEEP_WORKFLOW_PATH)
    assert "5-10 minutes" not in header
    assert "re-measured" in header.lower()
    recorded = _recorded_sweep_runs()
    times = _recorded_times(recorded)
    gaps = _recorded_gaps_minutes(recorded)
    days = (times[-1] - times[0]).total_seconds() / 86400
    assert f"{len(times)} runs in {days:.1f} days" in header
    assert f"{len(times) / days:.1f} a day" in header
    assert (
        f"minimum {round(min(gaps))}, median {round(statistics.median(gaps))}, maximum {round(max(gaps))} minutes"
        in header
    )
    assert f"{times[0].date()} to {times[-1].date()}" in header


def test_no_instruction_still_promises_the_sweep_runs_every_five_minutes() -> None:
    """Agents read these when deciding whether to wait or comment; the claim they act on must match the measurement."""
    assert "5-minute merge-admission sweep" not in GIT_INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    assert "5-minute schedule" not in WORKFLOW_PATH.read_text(encoding="utf-8")


# A comment on a pull request wakes the sweep. It does not wake merge-admission.yml: an `issue_comment` run
# is attached to the default branch's latest commit (GITHUB_SHA), not to the pull request's head, so a
# merge-admission run started that way could never replace the head's failed check. The sweep re-runs the
# head's own admission run, which does land on the head.

_EXPRESSION_TOKEN = re.compile(r"\s*(?:(?P<string>'[^']*')|(?P<op>\|\||&&|==|!=|\(|\))|(?P<path>[A-Za-z_][\w.\-]*))")


def _truthy(value: Any) -> bool:
    """GitHub's truthiness: false, 0, '' and null are falsy; anything else, including an object, is truthy."""
    return not (value is None or value is False or value == 0 or value == "")


def _evaluate_expression(expression: str, *, event_name: str, event: dict[str, Any]) -> Any:
    """Evaluate the small subset of GitHub's expression language a job condition here may use.

    Supports `||`, `&&`, `==`, `!=`, parentheses, string literals and `github.event_name` / `github.event.*`
    lookups. Anything else raises, so a condition that outgrows this fails the test loudly instead of being
    silently mis-evaluated.
    """
    tokens: list[tuple[str, str]] = []
    expression = expression.strip()
    position = 0
    while position < len(expression):
        match = _EXPRESSION_TOKEN.match(expression, position)
        if match is None or match.lastgroup is None:
            raise AssertionError(f"unsupported expression syntax near {expression[position:]!r}")
        tokens.append((match.lastgroup, match.group(match.lastgroup)))
        position = match.end()
    cursor = 0

    def peek() -> tuple[str, str] | None:
        return tokens[cursor] if cursor < len(tokens) else None

    def take() -> tuple[str, str]:
        nonlocal cursor
        token = tokens[cursor]
        cursor += 1
        return token

    def atom() -> Any:
        kind, text = take()
        if kind == "string":
            return text[1:-1]
        if kind == "op" and text == "(":
            value = disjunction()
            assert take() == ("op", ")")
            return value
        if kind != "path":
            raise AssertionError(f"unexpected token {text!r}")
        if text == "github.event_name":
            return event_name
        parts = text.split(".")
        assert parts[:2] == ["github", "event"], f"unsupported context {text!r}"
        value: Any = event
        for part in parts[2:]:
            value = value.get(part) if isinstance(value, dict) else None
        return value

    def comparison() -> Any:
        left = atom()
        if peek() in (("op", "=="), ("op", "!=")):
            operator = take()[1]
            right = atom()
            return (left == right) if operator == "==" else (left != right)
        return left

    def conjunction() -> Any:
        value = comparison()
        while peek() == ("op", "&&"):
            take()
            right = comparison()
            value = right if _truthy(value) else value
        return value

    def disjunction() -> Any:
        value = conjunction()
        while peek() == ("op", "||"):
            take()
            right = conjunction()
            value = value if _truthy(value) else right
        return value

    result = disjunction()
    assert cursor == len(tokens), f"unparsed tokens after {tokens[:cursor]!r}"
    return result


def _comment_event(*, on_pull_request: bool) -> dict[str, Any]:
    """An `issue_comment` payload, trimmed to the keys that matter: a PR comment carries `issue.pull_request`."""
    issue: dict[str, Any] = {"number": 310, "state": "open", "title": "[PIPELINE] P06: reuse one schema validator"}
    if on_pull_request:
        issue["pull_request"] = {"url": "https://api.github.com/repos/ZK-Theory/TDL/pulls/310"}
    return {
        "action": "created",
        "issue": issue,
        "comment": {"user": {"login": CODEX_BOT}, "body": "Codex Review: Didn't find any major issues."},
        "repository": {"default_branch": "main"},
    }


def _sweep_job_runs(event_name: str, event: dict[str, Any]) -> bool:
    """Whether GitHub would start the sweep job for this event, per the job's own `if` condition."""
    condition = _workflow_document(SWEEP_WORKFLOW_PATH)["jobs"]["sweep"].get("if")
    return True if condition is None else _truthy(_evaluate_expression(condition, event_name=event_name, event=event))


def test_a_comment_on_a_pull_request_wakes_the_sweep() -> None:
    """Watched failure: before this change the sweep had no comment trigger, so a Codex comment woke nothing."""
    triggers = _workflow_document(SWEEP_WORKFLOW_PATH)["on"]
    assert triggers["issue_comment"] == {"types": ["created"]}
    assert _sweep_job_runs("issue_comment", _comment_event(on_pull_request=True))


def test_a_comment_on_a_plain_issue_is_ignored() -> None:
    """`issue_comment` fires for issues as well; an issue has no pull request for the sweep to read."""
    assert not _sweep_job_runs("issue_comment", _comment_event(on_pull_request=False))


@pytest.mark.parametrize("event_name", ["schedule", "workflow_dispatch"])
def test_the_condition_does_not_switch_off_the_scheduled_or_manual_sweep(event_name: str) -> None:
    """Positive control: the condition that filters comments must not also filter the cron backstop."""
    assert _sweep_job_runs(event_name, {})


def test_comment_runs_and_scheduled_runs_share_one_serial_sweep_group() -> None:
    """Two sweeps must not act at once, and a newer one must not cancel one that is mid-way through a re-run."""
    concurrency = _workflow_document(SWEEP_WORKFLOW_PATH)["concurrency"]
    assert concurrency == {"group": "merge-admission-sweep", "cancel-in-progress": "false"}


def test_the_sweep_acts_on_nothing_the_comment_payload_carries() -> None:
    """Anyone can comment on a public pull request, and the sweep holds write scopes.

    The payload therefore only decides whether the job runs. No script and no action input may read the
    comment's author or body, or the issue's title or body, so a comment cannot steer what the sweep does.
    """
    body = SWEEP_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "github.event.comment" not in body
    for job in _workflow_document(SWEEP_WORKFLOW_PATH)["jobs"].values():
        for step in job["steps"]:
            assert "github.event.issue" not in step.get("run", ""), step.get("name")
            assert "github.event.comment" not in step.get("run", ""), step.get("name")


def test_only_the_sweep_reacts_to_comments() -> None:
    """A comment-triggered merge-admission run could only attach its check to the default branch's commit.

    `issue_comment` runs carry GITHUB_SHA of the default branch's latest commit, so the check would never
    replace the pull request head's, and the run would read green while changing nothing.
    """
    for path in WORKFLOW_FILES:
        reacts = "issue_comment" in _workflow_document(path)["on"]
        assert reacts == (path.name == "merge-admission-sweep.yml"), path.name


def test_a_codex_plus_one_and_its_no_issues_note_after_a_failed_admission_re_run_it(config: dict[str, Any]) -> None:
    """The sequence on PR #304: a +1, then a comment one second later, which is what wakes the sweep.

    The +1 is what the sweep reads. The comment must not hide it, and the re-run targets the head's own run.
    """
    pull_request = _failed_then_reacted(
        "2026-09-25T17:05:00Z",
        comment=("2026-09-25T17:05:01Z", "Codex Review: Didn't find any major issues. Nice work!"),
    )
    assert sweep_actions(_sweep_payload(pull_request), gate=_sweep_gate(config), producers=PRODUCERS) == [
        f"rerun {GATE_RUN_ID} 278"
    ]


def test_config_is_a_shallow_copy_not_shared(config: dict[str, Any], snapshot: dict[str, Any]) -> None:
    """Guard the fixtures themselves: mutation in one test must not leak."""
    mutated = copy.deepcopy(snapshot)
    _pull_request(mutated)["reviewThreads"]["nodes"] = []
    assert _pull_request(snapshot)["reviewThreads"]["nodes"], "snapshot fixture must be per-test"
    assert config["thread_finality"]["review_producers"]
