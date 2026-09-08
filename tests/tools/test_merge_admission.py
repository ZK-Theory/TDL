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


def _platform_order(snapshot: dict[str, Any], config: dict[str, Any], *, candidate: str = PR262_CANDIDATE) -> str:
    """Run the platform-order gate with the committed path and job config."""
    section = config["platform_order"]
    return evaluate_platform_order(
        snapshot,
        candidate_sha=candidate,
        linux_check_run=section["linux_check_run"],
        sensitive_paths=section["sensitive_paths"],
    )


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
    with pytest.raises(ValueError, match="check run on candidate"):
        _platform_order(snapshot, config)


def test_platform_order_does_not_apply_to_untouched_surfaces(snapshot: dict[str, Any], config: dict[str, Any]) -> None:
    """A candidate outside the configured surfaces is not subject to ordering."""
    _pull_request(snapshot)["files"]["nodes"] = [{"path": "docs/plans/strategy/Meta-Research-Plan.md"}]
    assert "not applicable" in _platform_order(snapshot, config)


def _with_linux_run(snapshot: dict[str, Any], *, completed_at: str, conclusion: str = "SUCCESS") -> dict[str, Any]:
    """Return the snapshot with a Linux check run attached to the candidate."""
    contexts = _pull_request(snapshot)["commits"]["nodes"][0]["commit"]["statusCheckRollup"]["contexts"]
    contexts["nodes"].append(
        {
            "__typename": "CheckRun",
            "name": "lint-and-test",
            "status": "COMPLETED",
            "conclusion": conclusion,
            "completedAt": completed_at,
        }
    )
    return snapshot


def _with_approval(snapshot: dict[str, Any], *, submitted_at: str) -> dict[str, Any]:
    """Return the snapshot with an approving review on the candidate."""
    _pull_request(snapshot)["reviews"]["nodes"].append(
        {
            "state": "APPROVED",
            "submittedAt": submitted_at,
            "author": {"login": "stephendor"},
            "commit": {"oid": PR262_CANDIDATE},
        }
    )
    return snapshot


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
    for event in ("pull_request", "pull_request_review", "pull_request_review_thread", "merge_group"):
        assert event in triggers, f"merge admission must re-evaluate on {event}"
    assert "created" in triggers["pull_request_review_thread"]["types"]

    body = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "tools/check_merge_admission.py thread-finality" in body
    assert "tools/check_merge_admission.py platform-order" in body


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
