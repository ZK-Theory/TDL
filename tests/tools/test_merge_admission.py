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
    evaluate_platform_order,
    evaluate_thread_finality,
    evidence_is_stale,
    load_config,
    main,
    path_is_sensitive,
    platform_status,
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
    section = config["platform_order"]
    return {
        "candidate_sha": candidate,
        "platform_sha": platform or candidate,
        "linux_check_run": section["linux_check_run"],
        "sensitive_paths": section["sensitive_paths"],
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


def test_store_changes_without_a_linux_run_are_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """PR #262 changed store code with no Linux job on the candidate at all."""
    with pytest.raises(ValueError, match="no 'lint-and-test' check run on"):
        _platform_order(snapshot, config)


def test_platform_order_does_not_apply_to_untouched_surfaces(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """A candidate outside the configured surfaces is not subject to ordering."""
    _pull_request(snapshot)["files"]["nodes"] = [{"path": "docs/plans/strategy/Meta-Research-Plan.md"}]
    assert "not applicable" in _platform_order(snapshot, config)


MERGE_GROUP_SHA = "0123456789abcdef0123456789abcdef01234567"


def _with_linux_run(
    snapshot: dict[str, Any],
    *,
    completed_at: str | None,
    conclusion: str | None = "SUCCESS",
    status: str = "COMPLETED",
) -> dict[str, Any]:
    """Return the snapshot with a Linux check run attached to the platform commit."""
    contexts = snapshot["data"]["repository"]["platformCommit"]["statusCheckRollup"]["contexts"]
    contexts["nodes"].append(
        {
            "__typename": "CheckRun",
            "name": "lint-and-test",
            "status": status,
            "conclusion": conclusion,
            "completedAt": completed_at,
        }
    )
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


def _as_merge_group(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the snapshot with the platform commit replaced by a queue commit carrying no checks yet."""
    snapshot["data"]["repository"]["platformCommit"] = {
        "oid": MERGE_GROUP_SHA,
        "statusCheckRollup": {"contexts": {"pageInfo": {"hasNextPage": False}, "nodes": []}},
    }
    return snapshot


# Codex review 3962013244: a superseded early approval must not keep the gate blocked.


def test_a_reapproval_after_green_linux_supersedes_the_early_one(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """The gate's own remediation -- re-request review -- must actually clear it."""
    _with_linux_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:10:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    assert "green before approval" in _platform_order(snapshot, config)


def test_another_reviewers_early_approval_still_blocks(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Supersession is per reviewer: one reviewer's re-approval does not clear another's."""
    _with_linux_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:10:00Z", login="independent-reviewer")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    with pytest.raises(ValueError, match="independent-reviewer at 2026-08-23T07:10:00Z"):
        _platform_order(snapshot, config)


# Codex review 3962013225: inside a merge queue the evidence must come from the queue commit.


def test_merge_group_candidate_is_not_certified_by_the_pr_heads_checks(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Green Linux on the pre-queue head says nothing about the integrated commit."""
    _as_merge_group(snapshot)
    with pytest.raises(ValueError, match=f"no 'lint-and-test' check run on {MERGE_GROUP_SHA}"):
        _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)


def test_merge_group_candidate_with_green_linux_on_the_queue_commit_is_admitted(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Positive control: the same queue commit passes once its own Linux lane is green."""
    _as_merge_group(snapshot)
    _with_linux_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    assert "green before approval" in _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)


def test_a_snapshot_for_the_wrong_platform_commit_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Checks read from one commit cannot be attributed to another."""
    with pytest.raises(ValueError, match=f"is not '{MERGE_GROUP_SHA}'"):
        _platform_order(snapshot, config, platform=MERGE_GROUP_SHA)


# Codex review 3962013214: a still-running Linux lane is a reason to wait, not to fail.


def test_platform_status_is_pending_before_the_linux_lane_registers(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """PR #262's candidate has sensitive paths and no Linux run: wait, do not decide."""
    assert _platform_status(snapshot, config) == "pending"


def test_platform_status_is_pending_while_the_linux_lane_runs(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """An in-progress run is not terminal evidence in either direction."""
    _with_linux_run(snapshot, completed_at=None, conclusion=None, status="IN_PROGRESS")
    assert _platform_status(snapshot, config) == "pending"


def test_platform_status_is_ready_once_the_linux_lane_completes(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Completion ends the wait even on failure; the gate then decides."""
    _with_linux_run(snapshot, completed_at="2026-08-23T07:30:00Z", conclusion="FAILURE")
    assert _platform_status(snapshot, config) == "ready"


def test_platform_status_never_waits_on_untouched_surfaces(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """Only the candidates the ordering rule governs spend runner time waiting."""
    _pull_request(snapshot)["files"]["nodes"] = [{"path": "docs/plans/strategy/Meta-Research-Plan.md"}]
    assert _platform_status(snapshot, config) == "not-applicable"


def test_an_in_progress_linux_lane_still_blocks_the_gate_itself(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """If the wait budget runs out, the gate fails closed rather than passing."""
    _with_linux_run(snapshot, completed_at=None, conclusion=None, status="IN_PROGRESS")
    with pytest.raises(ValueError, match="'IN_PROGRESS'"):
        _platform_order(snapshot, config)


def test_approval_before_linux_evidence_is_refused(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The PR #263 shape: acceptance recorded ahead of the decisive platform run."""
    _with_linux_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:10:00Z")
    with pytest.raises(ValueError, match="approval preceded Linux evidence"):
        _platform_order(snapshot, config)


def test_approval_after_green_linux_evidence_is_admitted(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """The corrected ordering passes, so the block above is caused by ordering."""
    _with_linux_run(snapshot, completed_at="2026-08-23T07:30:00Z")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    verdict = _platform_order(snapshot, config)
    assert "research_system/store/lock.py" in verdict


def test_a_failing_linux_run_is_refused_regardless_of_ordering(
    snapshot: dict[str, Any], config: dict[str, Any]
) -> None:
    """Ordering is necessary, not sufficient: the platform evidence must be green."""
    _with_linux_run(snapshot, completed_at="2026-08-23T07:30:00Z", conclusion="FAILURE")
    _with_approval(snapshot, submitted_at="2026-08-23T07:45:00Z")
    with pytest.raises(ValueError, match="concluded 'FAILURE'"):
        _platform_order(snapshot, config)


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


def test_workflow_waits_for_a_pending_linux_lane_before_deciding() -> None:
    """Codex review 3962013214: a running Linux lane is polled, not failed on sight."""
    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "tools/check_merge_admission.py platform-status" in body
    assert 'while [ "$(status_of)" = "pending" ]' in body


def test_configured_linux_job_exists_in_ci() -> None:
    """The gate's configured check-run name must name a real CI job."""
    config = load_config(CONFIG_PATH)
    ci = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    linux_job = config["platform_order"]["linux_check_run"]
    assert linux_job in ci["jobs"], f"{linux_job} is not a job in ci.yml"
    assert ci["jobs"][linux_job]["runs-on"].startswith("ubuntu"), f"{linux_job} must run on Linux"


def test_config_is_a_shallow_copy_not_shared(config: dict[str, Any], snapshot: dict[str, Any]) -> None:
    """Guard the fixtures themselves: mutation in one test must not leak."""
    mutated = copy.deepcopy(snapshot)
    _pull_request(mutated)["reviewThreads"]["nodes"] = []
    assert _pull_request(snapshot)["reviewThreads"]["nodes"], "snapshot fixture must be per-test"
    assert config["thread_finality"]["review_producers"]
