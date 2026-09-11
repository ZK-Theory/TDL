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
from pathlib import Path
from typing import Any

import pytest
import yaml

from tools.check_merge_admission import (
    evaluate_merge_group_size,
    evaluate_platform_order,
    evaluate_thread_finality,
    evidence_is_stale,
    load_config,
    main,
    path_is_sensitive,
    platform_producer,
    platform_status,
    queue_disposition,
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


def test_a_graphql_error_response_is_refused(config: dict[str, Any]) -> None:
    """A failed query is absence of evidence, not evidence of a clean candidate."""
    with pytest.raises(ValueError, match="carries errors"):
        evaluate_thread_finality(
            {"errors": [{"message": "rate limited"}]},
            candidate_sha=PR262_CANDIDATE,
            review_producers=config["thread_finality"]["review_producers"],
        )


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
) -> dict[str, Any]:
    """Return a `windows-store-lock` check run, trusted unless ``suite`` says otherwise."""
    return {
        "__typename": "CheckRun",
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


def test_config_is_a_shallow_copy_not_shared(config: dict[str, Any], snapshot: dict[str, Any]) -> None:
    """Guard the fixtures themselves: mutation in one test must not leak."""
    mutated = copy.deepcopy(snapshot)
    _pull_request(mutated)["reviewThreads"]["nodes"] = []
    assert _pull_request(snapshot)["reviewThreads"]["nodes"], "snapshot fixture must be per-test"
    assert config["thread_finality"]["review_producers"]
