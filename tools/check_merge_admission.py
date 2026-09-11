#!/usr/bin/env python3
# Research context: TDA-Research/03-Papers/P06/_project.md
# Purpose: fail merge admission closed when review-thread finality or
# platform-evidence ordering cannot be established at the exact merge candidate.
"""Merge-admission gates evaluated against a single evidence snapshot.

Five gates. The first two derive from recorded Gate 6 failures; the last three
close merge-queue and thread-state gaps found in review of PR #278:

``thread-finality``
    Observation ``01M0PWSR73ABY48X8YW7KQX6Q6``. PR #262 merged 89 seconds after
    five Codex review threads were published; the clean-thread readback that
    admitted it was taken before those threads existed. Thread finality is a
    property of the exact merge candidate, so it is re-derived here from a
    snapshot bound to ``headRefOid`` and never carried forward.

``platform-order``
    Observation ``01M0Q0WXJSCX5WJ69H2G9DG4E3``. PR #263's first head was
    accepted while the decisive platform controls had not run; the platform
    workflow then failed. For candidates touching filesystem/concurrency
    surfaces, the configured platform job must be terminal and green before any
    approving review is submitted. The project supports Windows only (decided
    2026-09-11), so that job is ``windows-store-lock``.

``queue-disposition`` and ``merge-group-size``
    A merge-queue commit's green check cannot see review changes made after it
    was built, and a batched group would certify several pull requests on one
    pull request's evidence. The first removes a queued pull request when its
    review state changes; the second refuses a queue commit carrying more
    entries than configured.

``sweep``
    Reopening a resolved thread emits no Actions event, so a green admission
    check can outlive a newly live blocker. Run on a schedule, this lists what
    must happen for every open pull request with a live thread: dequeue it if
    queued, and re-run a currently green admission check.

Every gate raises :class:`ValueError` on absent, malformed, truncated, or
untrusted evidence: silent absence is the failure mode these gates exist to
remove.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(".github/merge-admission.yml")
_GLOB_METACHARACTERS = ("*", "?", "[")


def _require_mapping(value: object, what: str) -> Mapping[str, Any]:
    """Return ``value`` as a mapping or raise with a locating message."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{what} must be a JSON object, got {type(value).__name__}")
    return value


def _require_nodes(connection: object, what: str) -> list[Mapping[str, Any]]:
    """Return a GraphQL connection's nodes, refusing truncated pages."""
    conn = _require_mapping(connection, what)
    page_info = conn.get("pageInfo")
    if not isinstance(page_info, Mapping) or "hasNextPage" not in page_info:
        raise ValueError(f"{what} is missing pageInfo.hasNextPage; evidence completeness is unknown")
    if page_info["hasNextPage"]:
        raise ValueError(f"{what} is truncated (hasNextPage=true); refusing to admit on partial evidence")
    nodes = conn.get("nodes")
    if not isinstance(nodes, list) or not all(isinstance(node, Mapping) for node in nodes):
        raise ValueError(f"{what} must contain a list of node objects")
    return list(nodes)


def _repository(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Extract the repository object from a raw ``gh api graphql`` response."""
    if "errors" in payload:
        raise ValueError(f"GraphQL response carries errors: {payload['errors']!r}")
    data = _require_mapping(payload.get("data"), "response.data")
    return _require_mapping(data.get("repository"), "response.data.repository")


def _pull_request(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Extract the pullRequest object from a raw ``gh api graphql`` response."""
    repository = _repository(payload)
    return _require_mapping(repository.get("pullRequest"), "response.data.repository.pullRequest")


def _parse_timestamp(value: object, what: str) -> datetime:
    """Parse a GitHub ISO-8601 timestamp, raising on anything unusable."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty ISO-8601 timestamp")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{what} is not a parseable ISO-8601 timestamp: {value!r}") from exc


def _assert_candidate(pull_request: Mapping[str, Any], candidate_sha: str) -> None:
    """Refuse evidence whose head is not the candidate being admitted."""
    if not candidate_sha:
        raise ValueError("candidate sha must be supplied; admission cannot be evaluated without one")
    head = pull_request.get("headRefOid")
    if head != candidate_sha:
        raise ValueError(f"evidence head {head!r} is not the merge candidate {candidate_sha!r}; snapshot is stale")


def _thread_author(thread: Mapping[str, Any]) -> str:
    """Return the login that opened a review thread, or ``"unknown"``."""
    comments = thread.get("comments")
    if not isinstance(comments, Mapping):
        return "unknown"
    nodes = comments.get("nodes")
    if not isinstance(nodes, list) or not nodes or not isinstance(nodes[0], Mapping):
        return "unknown"
    author = nodes[0].get("author")
    if not isinstance(author, Mapping):
        return "unknown"
    return str(author.get("login", "unknown"))


def _thread_opened_at(thread: Mapping[str, Any]) -> datetime:
    """Return the creation time of a review thread's first comment."""
    comments = _require_mapping(thread.get("comments"), "reviewThread.comments")
    nodes = comments.get("nodes")
    if not isinstance(nodes, list) or not nodes or not isinstance(nodes[0], Mapping):
        raise ValueError("reviewThread.comments.nodes must contain at least one comment")
    return _parse_timestamp(nodes[0].get("createdAt"), "reviewThread first comment createdAt")


def _review_rows(pull_request: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the PR's submitted reviews as validated node mappings."""
    return _require_nodes(pull_request.get("reviews"), "pullRequest.reviews")


def _review_login(review: Mapping[str, Any]) -> str:
    """Return a review's author login, or ``"unknown"`` for a deleted account."""
    author = review.get("author")
    if not isinstance(author, Mapping):
        return "unknown"
    return str(author.get("login", "unknown"))


def _review_commit(review: Mapping[str, Any]) -> str | None:
    """Return the commit oid a review was submitted against, if recorded."""
    commit = review.get("commit")
    if not isinstance(commit, Mapping):
        return None
    oid = commit.get("oid")
    return str(oid) if isinstance(oid, str) else None


def evaluate_thread_finality(
    payload: Mapping[str, Any],
    *,
    candidate_sha: str,
    review_producers: Sequence[str],
) -> None:
    """Admit only when every producer is terminal and no live thread remains.

    Args:
        payload: Raw ``gh api graphql`` response for the pull request.
        candidate_sha: The exact merge candidate the evidence must describe.
        review_producers: Logins that must have reviewed the candidate itself.

    Raises:
        ValueError: If the evidence is stale, truncated, malformed, a configured
            producer has not reached a terminal state on the candidate, or any
            unresolved non-outdated review thread remains.
    """
    pull_request = _pull_request(payload)
    _assert_candidate(pull_request, candidate_sha)

    reviews = _review_rows(pull_request)
    terminal = {_review_login(review) for review in reviews if _review_commit(review) == candidate_sha}
    pending = [producer for producer in review_producers if producer not in terminal]
    if pending:
        raise ValueError(
            "review producers have not reached a terminal state on the candidate: " + ", ".join(sorted(pending))
        )

    threads = _require_nodes(pull_request.get("reviewThreads"), "pullRequest.reviewThreads")
    for index, thread in enumerate(threads):
        if "isResolved" not in thread or "isOutdated" not in thread:
            raise ValueError(f"reviewThreads.nodes[{index}] is missing isResolved/isOutdated")
    live = [thread for thread in threads if not thread["isResolved"] and not thread["isOutdated"]]
    if live:
        authors = sorted({_thread_author(thread) for thread in live})
        raise ValueError(
            f"{len(live)} unresolved non-outdated review thread(s) on candidate {candidate_sha} "
            f"from {', '.join(authors)}; each needs a recorded disposition before admission"
        )


def evidence_is_stale(payload: Mapping[str, Any], *, evidence_recorded_at: str) -> bool:
    """Report whether a thread published after ``evidence_recorded_at`` exists.

    A clean-thread readback is only evidence for the moment it was taken. Any
    non-outdated thread opened after that moment invalidates it, which is the
    exact 89-second window that admitted PR #262.

    Args:
        payload: Raw ``gh api graphql`` response for the pull request.
        evidence_recorded_at: ISO-8601 timestamp of the earlier clean readback.

    Returns:
        ``True`` when prior clean-thread evidence must be re-derived.

    Raises:
        ValueError: If the snapshot or the timestamp cannot be parsed.
    """
    recorded_at = _parse_timestamp(evidence_recorded_at, "evidence_recorded_at")
    pull_request = _pull_request(payload)
    threads = _require_nodes(pull_request.get("reviewThreads"), "pullRequest.reviewThreads")
    return any(not thread.get("isOutdated") and _thread_opened_at(thread) > recorded_at for thread in threads)


def path_is_sensitive(path: str, patterns: Iterable[str]) -> bool:
    """Return whether one changed path matches any platform-sensitive pattern."""
    for pattern in patterns:
        if any(char in pattern for char in _GLOB_METACHARACTERS):
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern.removeprefix("**/")):
                return True
        elif path == pattern or path.startswith(pattern):
            return True
    return False


@dataclass(frozen=True)
class PlatformProducer:
    """The single trusted source of platform evidence.

    Attributes:
        check_run: Check-run name of the decisive platform job.
        workflow_path: Repository path of the workflow that must produce it.
        app_slug: GitHub App that must own the check suite.
    """

    check_run: str
    workflow_path: str
    app_slug: str


def _changed_paths(payload: Mapping[str, Any]) -> list[str]:
    """Return every path the candidate touches, rename sources included.

    GraphQL ``PullRequest.files`` reports only a rename's destination, so a
    sensitive file renamed to a non-matching name escaped the gate (Codex review
    3988684695). The REST files listing carries ``previous_filename``; the
    snapshot embeds it as ``restFiles``, and its length is checked against
    GraphQL's ``changedFiles`` so a truncated listing cannot pass as complete.
    """
    pull_request = _pull_request(payload)
    rows = payload.get("restFiles")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("snapshot carries no restFiles list; the candidate's changed paths are unknown")
    expected = pull_request.get("changedFiles")
    if not isinstance(expected, int) or isinstance(expected, bool):
        raise ValueError("pullRequest.changedFiles is missing; file-list completeness is unknown")
    if len(rows) != expected:
        raise ValueError(
            f"restFiles lists {len(rows)} files but the pull request changes {expected}; listing is incomplete"
        )
    paths: list[str] = []
    for index, row in enumerate(rows):
        filename = row.get("filename")
        if not isinstance(filename, str) or not filename:
            raise ValueError(f"restFiles[{index}].filename is missing")
        paths.append(filename)
        previous = row.get("previous_filename")
        if previous is not None:
            if not isinstance(previous, str) or not previous:
                raise ValueError(f"restFiles[{index}].previous_filename is present but empty")
            paths.append(previous)
    return paths


def _rollup_nodes(commit: object, *, expected_oid: str, what: str) -> list[Mapping[str, Any]]:
    """Return a commit's status-check contexts after binding it to ``expected_oid``."""
    if commit is None:
        raise ValueError(f"snapshot carries no {what} for {expected_oid}; platform evidence is absent")
    commit = _require_mapping(commit, what)
    if commit.get("oid") != expected_oid:
        raise ValueError(f"{what} {commit.get('oid')!r} is not {expected_oid!r}")
    rollup = commit.get("statusCheckRollup")
    if rollup is None:
        # No checks have registered on this commit yet. That is a legitimate
        # transient state, distinct from a failed query, so it is reported as
        # zero contexts and the caller decides whether to block or wait.
        return []
    return _require_nodes(_require_mapping(rollup, "statusCheckRollup").get("contexts"), f"{what}.contexts")


def _head_contexts(payload: Mapping[str, Any], candidate_sha: str) -> list[Mapping[str, Any]]:
    """Return the status-check contexts on the pull request head."""
    commits = _require_nodes(_pull_request(payload).get("commits"), "pullRequest.commits")
    if len(commits) != 1:
        raise ValueError(f"expected exactly one tip commit in the snapshot, got {len(commits)}")
    return _rollup_nodes(commits[0].get("commit"), expected_oid=candidate_sha, what="head commit")


def _platform_contexts(payload: Mapping[str, Any], platform_sha: str) -> list[Mapping[str, Any]]:
    """Return the status-check contexts on the merge-group commit."""
    return _rollup_nodes(_repository(payload).get("platformCommit"), expected_oid=platform_sha, what="platform commit")


def _platform_check(
    contexts: Sequence[Mapping[str, Any]], *, producer: PlatformProducer, sha: str
) -> Mapping[str, Any] | None:
    """Return the current trusted platform check run on one commit, or ``None`` if absent.

    A check run is identified by name alone in the rollup, and any workflow can
    publish a check with that name. Evidence is accepted only from the
    configured app and workflow file (Codex review 3988684703).

    A re-run leaves every attempt in the rollup: commit 2146780 carried a
    FAILURE and a later CANCELLED ``merge-admission`` run side by side.
    Check-run ids increase with creation, so the highest trusted id is the
    current attempt, and earlier attempts are history rather than ambiguity
    (Codex review 3990012209).

    Raises:
        ValueError: If a same-named check run comes from any other producer,
            or a trusted run carries no ``databaseId`` to order attempts by.
    """
    trusted: list[Mapping[str, Any]] = []
    for context in contexts:
        if context.get("__typename") != "CheckRun" or context.get("name") != producer.check_run:
            continue
        suite = context.get("checkSuite")
        suite = suite if isinstance(suite, Mapping) else {}
        app = suite.get("app")
        slug = app.get("slug") if isinstance(app, Mapping) else None
        run = suite.get("workflowRun")
        file = run.get("file") if isinstance(run, Mapping) else None
        path = file.get("path") if isinstance(file, Mapping) else None
        if slug != producer.app_slug or path != producer.workflow_path:
            # Job-level permissions set unlisted scopes to none, and the token
            # needs `actions: read` to see workflowRun (Codex review 3990012219).
            hint = (
                ""
                if isinstance(run, Mapping)
                else "; workflowRun was unavailable, so check the job grants actions: read"
            )
            raise ValueError(
                f"{producer.check_run!r} on {sha} was produced by app {slug!r} from {path!r}, not "
                f"{producer.app_slug!r} from {producer.workflow_path!r}; refusing untrusted platform evidence{hint}"
            )
        check_id = context.get("databaseId")
        if not isinstance(check_id, int) or isinstance(check_id, bool):
            raise ValueError(f"{producer.check_run!r} on {sha} carries no databaseId; its latest attempt is unknown")
        trusted.append(context)
    if not trusted:
        return None
    return max(trusted, key=lambda context: context["databaseId"])


def _platform_commits(payload: Mapping[str, Any], *, candidate_sha: str, platform_sha: str) -> list[tuple[str, Any]]:
    """Return ``(sha, contexts)`` for every commit whose platform run must be green."""
    commits: list[tuple[str, Any]] = [(candidate_sha, _head_contexts(payload, candidate_sha))]
    if platform_sha != candidate_sha:
        commits.append((platform_sha, _platform_contexts(payload, platform_sha)))
    return commits


def platform_status(
    payload: Mapping[str, Any],
    *,
    candidate_sha: str,
    platform_sha: str,
    producer: PlatformProducer,
    sensitive_paths: Sequence[str],
) -> str:
    """Report whether the platform gate can be decided yet.

    ``pull_request: synchronize`` starts this gate alongside CI, so the platform
    job is routinely queued or in progress when the first snapshot is taken. No
    event fires when it later completes, so failing at that moment would leave a
    permanently red check on a candidate that is actually fine. The caller waits
    on ``pending`` instead. Inside a merge queue both the pull request head and
    the queue commit must be terminal.

    Args:
        payload: Evidence snapshot for the pull request.
        candidate_sha: The exact merge candidate the evidence must describe.
        platform_sha: The merge-group commit inside a queue, else the candidate.
        producer: Trusted producer of the platform check run.
        sensitive_paths: Filesystem/concurrency path prefixes and globs.

    Returns:
        ``"not-applicable"``, ``"pending"``, or ``"ready"``.

    Raises:
        ValueError: If the evidence is stale, truncated, malformed, or untrusted.
    """
    pull_request = _pull_request(payload)
    _assert_candidate(pull_request, candidate_sha)
    if not any(path_is_sensitive(path, sensitive_paths) for path in _changed_paths(payload)):
        return "not-applicable"
    for sha, contexts in _platform_commits(payload, candidate_sha=candidate_sha, platform_sha=platform_sha):
        run = _platform_check(contexts, producer=producer, sha=sha)
        if run is None or run.get("status") != "COMPLETED":
            return "pending"
    return "ready"


def _require_green(run: Mapping[str, Any] | None, *, producer: PlatformProducer, sha: str, touched: str) -> datetime:
    """Return a platform run's completion time, raising unless it passed."""
    if run is None:
        raise ValueError(f"no {producer.check_run!r} check run on {sha}; platform-sensitive paths changed: {touched}")
    if run.get("status") != "COMPLETED":
        raise ValueError(f"{producer.check_run} is {run.get('status')!r} on {sha}, not COMPLETED")
    if run.get("conclusion") != "SUCCESS":
        raise ValueError(f"{producer.check_run} concluded {run.get('conclusion')!r} on {sha}, not SUCCESS")
    return _parse_timestamp(run.get("completedAt"), f"{producer.check_run}.completedAt")


def _latest_approvals(pull_request: Mapping[str, Any], candidate_sha: str) -> dict[str, Mapping[str, Any]]:
    """Return each reviewer's most recent approval of the candidate.

    GitHub keeps every review record, so an approval submitted before the platform
    job finished survives a later re-approval of the same commit. Only the
    latest one per reviewer is the reviewer's live position; judging the
    superseded record would leave the gate blocked with no reachable remedy.
    """
    latest: dict[str, Mapping[str, Any]] = {}
    for review in _review_rows(pull_request):
        if review.get("state") != "APPROVED" or _review_commit(review) != candidate_sha:
            continue
        login = _review_login(review)
        submitted_at = _parse_timestamp(review.get("submittedAt"), "review.submittedAt")
        current = latest.get(login)
        if current is None or submitted_at > _parse_timestamp(current.get("submittedAt"), "review.submittedAt"):
            latest[login] = review
    return latest


def evaluate_platform_order(
    payload: Mapping[str, Any],
    *,
    candidate_sha: str,
    platform_sha: str,
    producer: PlatformProducer,
    sensitive_paths: Sequence[str],
) -> str:
    """Require green platform evidence before approval on platform-sensitive code.

    Ordering is judged on the pull request head, because that is the commit
    reviewers approve. Inside a merge queue the approvals necessarily predate
    the queue commit's run, so comparing them against it would reject every
    queued candidate (Codex review 3988684687); the queue commit's run must
    instead pass on its own.

    Args:
        payload: Evidence snapshot for the pull request.
        candidate_sha: The exact merge candidate the evidence must describe.
        platform_sha: The merge-group commit inside a queue, else the candidate.
        producer: Trusted producer of the platform check run.
        sensitive_paths: Filesystem/concurrency path prefixes and globs.

    Returns:
        A one-line human-readable verdict for the passing cases.

    Raises:
        ValueError: If the evidence is stale, truncated, malformed, or untrusted;
            if the candidate edits the workflow that produces its own platform
            evidence; if the platform run is absent, non-terminal, or failing
            on the head or the queue commit; or if a reviewer's live approval of
            the candidate was submitted before the head run concluded.
    """
    pull_request = _pull_request(payload)
    _assert_candidate(pull_request, candidate_sha)

    changed = _changed_paths(payload)
    touched = sorted({path for path in changed if path_is_sensitive(path, sensitive_paths)})
    if not touched:
        return "platform-order: not applicable (no filesystem or concurrency paths changed)"
    if producer.workflow_path in changed:
        # A pull_request run executes the candidate's own copy of the workflow,
        # so the producer check above would still see the trusted file path
        # while the job itself had been rewritten to pass.
        raise ValueError(
            f"the candidate changes {producer.workflow_path}, which produces its own platform evidence; this gate "
            "cannot certify it -- land the workflow change in a separate pull request"
        )
    touched_text = ", ".join(touched)

    head_run = _platform_check(_head_contexts(payload, candidate_sha), producer=producer, sha=candidate_sha)
    completed_at = _require_green(head_run, producer=producer, sha=candidate_sha, touched=touched_text)

    early = []
    for login, review in _latest_approvals(pull_request, candidate_sha).items():
        if _parse_timestamp(review.get("submittedAt"), "review.submittedAt") <= completed_at:
            early.append(f"{login} at {review['submittedAt']}")
    if early:
        raise ValueError(
            f"approval preceded platform evidence ({producer.check_run} completed {completed_at.isoformat()} "
            f"on {candidate_sha}): " + "; ".join(sorted(early)) + "; re-request review against the green candidate"
        )

    verdict = f"platform-order: {producer.check_run} green before approval; sensitive paths: {touched_text}"
    if platform_sha == candidate_sha:
        return verdict
    queue_run = _platform_check(_platform_contexts(payload, platform_sha), producer=producer, sha=platform_sha)
    _require_green(queue_run, producer=producer, sha=platform_sha, touched=touched_text)
    return f"{verdict}; also green on merge-group commit {platform_sha}"


REVIEW_EVENTS = frozenset({"pull_request_review", "pull_request_review_comment"})


def queue_disposition(payload: Mapping[str, Any], *, event_name: str) -> str:
    """Decide whether a review change must remove the pull request from the merge queue.

    A merge-group run evaluates threads once, when the queue commit is built.
    Later review events re-run this gate on the pull request head only, so a
    thread opened on a queued pull request never reaches the queue commit's
    green check (Codex review 3988684692). Removing the entry forces the queue
    to rebuild, which re-evaluates admission from current review state.

    Args:
        payload: ``gh api graphql`` response carrying ``pullRequest.mergeQueueEntry``.
        event_name: The GitHub event that triggered this run.

    Returns:
        ``"dequeue"`` or ``"keep"``.

    Raises:
        ValueError: If the snapshot does not state queue membership.
    """
    pull_request = _pull_request(payload)
    if "mergeQueueEntry" not in pull_request:
        raise ValueError("pullRequest.mergeQueueEntry is absent from the snapshot; queue membership is unknown")
    entry = pull_request["mergeQueueEntry"]
    if event_name not in REVIEW_EVENTS or entry is None:
        return "keep"
    _require_mapping(entry, "pullRequest.mergeQueueEntry")
    return "dequeue"


def evaluate_merge_group_size(compare: Mapping[str, Any], *, base_sha: str, head_sha: str, max_entries: int) -> str:
    """Refuse a merge-group commit that batches more pull requests than allowed.

    Admission evaluates the single pull request named in the queue ref, so a
    batched group would certify every other entry on that one pull request's
    threads and files (Codex review 3988684699). The P-049 ruleset builds and
    merges one entry at a time; this re-derives that from the commit itself, so
    a later ruleset change cannot silently widen what one evaluation certifies.
    Entries are squash-merged, so entries equal commits between the merge base
    and the queue head.

    Args:
        compare: REST ``compare/{base}...{head}`` response.
        base_sha: The merge group's base commit.
        head_sha: The merge group's synthetic head commit.
        max_entries: Largest group admission may certify.

    Returns:
        A one-line human-readable verdict.

    Raises:
        ValueError: If the comparison is malformed, is not rooted at the base, or
            counts more entries than ``max_entries``.
    """
    merge_base = _require_mapping(compare.get("merge_base_commit"), "compare.merge_base_commit")
    if merge_base.get("sha") != base_sha:
        raise ValueError(
            f"merge-group commit {head_sha} is not built on base {base_sha} (merge base {merge_base.get('sha')!r})"
        )
    total = compare.get("total_commits")
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        raise ValueError(f"compare {base_sha}...{head_sha} reports no commits; merge-group entries cannot be counted")
    if total > max_entries:
        raise ValueError(
            f"merge-group commit {head_sha} carries {total} entries; admission evaluates one pull request at a time, "
            f"so at most {max_entries} is allowed"
        )
    return f"merge-group-size: {total} entry on {head_sha} (limit {max_entries})"


@dataclass(frozen=True)
class SweepGate:
    """The admission check a sweep re-runs, identified by producer as well as name.

    Attributes:
        check_run: Check-run name of the admission job.
        workflow_path: Repository path of the workflow that produces it.
    """

    check_run: str
    workflow_path: str


def _live_thread_count(pull_request: Mapping[str, Any], what: str) -> int:
    """Return the number of unresolved, non-outdated review threads."""
    threads = _require_nodes(pull_request.get("reviewThreads"), f"{what}.reviewThreads")
    for index, thread in enumerate(threads):
        if "isResolved" not in thread or "isOutdated" not in thread:
            raise ValueError(f"{what}.reviewThreads.nodes[{index}] is missing isResolved/isOutdated")
    return sum(1 for thread in threads if not thread["isResolved"] and not thread["isOutdated"])


def _green_gate_runs(pull_request: Mapping[str, Any], *, gate: SweepGate, what: str) -> list[int]:
    """Return the workflow-run id of the head's current admission check, if it is green.

    Only the latest attempt is judged: an older green attempt followed by a
    failing re-run already reflects the live thread, and re-running the old
    success would be noise (Codex review 3990012209).
    """
    commits = _require_nodes(pull_request.get("commits"), f"{what}.commits")
    if len(commits) != 1:
        raise ValueError(f"{what}: expected exactly one tip commit, got {len(commits)}")
    commit = _require_mapping(commits[0].get("commit"), f"{what} head commit")
    rollup = commit.get("statusCheckRollup")
    if rollup is None:
        return []
    contexts = _require_nodes(_require_mapping(rollup, f"{what} statusCheckRollup").get("contexts"), f"{what} contexts")
    latest: Mapping[str, Any] | None = None
    latest_run: Mapping[str, Any] | None = None
    for context in contexts:
        if context.get("__typename") != "CheckRun" or context.get("name") != gate.check_run:
            continue
        suite = context.get("checkSuite")
        run = suite.get("workflowRun") if isinstance(suite, Mapping) else None
        file = run.get("file") if isinstance(run, Mapping) else None
        if not isinstance(run, Mapping) or not isinstance(file, Mapping) or file.get("path") != gate.workflow_path:
            continue
        check_id = context.get("databaseId")
        if not isinstance(check_id, int) or isinstance(check_id, bool):
            raise ValueError(f"{what}: a {gate.check_run} check carries no databaseId; its latest attempt is unknown")
        if latest is None or check_id > latest["databaseId"]:
            latest, latest_run = context, run
    if latest is None or latest_run is None or latest.get("conclusion") != "SUCCESS":
        return []
    run_id = latest_run.get("databaseId")
    if not isinstance(run_id, int) or isinstance(run_id, bool):
        raise ValueError(f"{what}: a green {gate.check_run} check carries no workflow run id, so it cannot be re-run")
    return [run_id]


def sweep_actions(payload: Mapping[str, Any], *, gate: SweepGate) -> list[str]:
    """Return what a scheduled sweep must do for open pull requests with live threads.

    Reopening a resolved thread (``unresolveReviewThread``) emits no Actions
    event, so a green admission check can outlive a newly live blocker (Codex
    review 3988790015). A pull request with at least one unresolved,
    non-outdated thread yields:

    - ``dequeue <pull-request-id> <number>`` if it is in the merge queue;
    - ``rerun <workflow-run-id> <number>`` for each currently green admission
      check on its head, so the re-run replaces that success on the same commit.

    Pull requests with no live thread, and admission checks that are already
    failing or still running, need nothing and yield nothing, so repeated sweeps
    do not pile up re-runs.

    Args:
        payload: ``gh api graphql`` response listing open pull requests.
        gate: The admission check to re-run.

    Returns:
        Action lines in pull-request order.

    Raises:
        ValueError: If the listing or any nested connection is truncated or
            malformed, or queue membership is not stated.
    """
    pulls = _require_nodes(_repository(payload).get("pullRequests"), "repository.pullRequests")
    actions: list[str] = []
    for pull_request in pulls:
        number = pull_request.get("number")
        if not isinstance(number, int) or isinstance(number, bool):
            raise ValueError("a repository.pullRequests node is missing its number")
        what = f"pull request #{number}"
        if _live_thread_count(pull_request, what) == 0:
            continue
        pull_request_id = pull_request.get("id")
        if not isinstance(pull_request_id, str) or not pull_request_id:
            raise ValueError(f"{what} is missing its node id")
        if "mergeQueueEntry" not in pull_request:
            raise ValueError(f"{what}.mergeQueueEntry is absent; queue membership is unknown")
        if pull_request["mergeQueueEntry"] is not None:
            actions.append(f"dequeue {pull_request_id} {number}")
        actions.extend(f"rerun {run_id} {number}" for run_id in _green_gate_runs(pull_request, gate=gate, what=what))
    return actions


def load_config(path: Path) -> Mapping[str, Any]:
    """Load and shallow-validate the merge-admission configuration file."""
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError(f"{path} must contain a YAML mapping")
    return config


def _section(config: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    """Return one configuration section, raising when it is absent."""
    section = config.get(name)
    if not isinstance(section, Mapping):
        raise ValueError(f"configuration is missing the {name!r} section")
    return section


def _string_list(section: Mapping[str, Any], key: str) -> list[str]:
    """Return a configured list of strings, raising on any other shape."""
    values = section.get(key)
    if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
        raise ValueError(f"configuration key {key!r} must be a non-empty list of strings")
    return list(values)


def platform_producer(config: Mapping[str, Any]) -> PlatformProducer:
    """Return the configured trusted producer of platform evidence."""
    section = _section(config, "platform_order")
    values: dict[str, str] = {}
    for key in ("check_run", "workflow_path", "app_slug"):
        value = section.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"configuration key 'platform_order.{key}' must be a non-empty string")
        values[key] = value
    return PlatformProducer(**values)


def _max_entries(config: Mapping[str, Any]) -> int:
    """Return the configured largest merge group admission may certify."""
    value = _section(config, "merge_queue").get("max_entries")
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("configuration key 'merge_queue.max_entries' must be a positive integer")
    return value


def _load_json(path: Path | None, flag: str) -> Mapping[str, Any]:
    """Load a JSON object named by a command-line flag."""
    if path is None:
        raise ValueError(f"{flag} is required for this gate")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{flag} must contain a JSON object")
    return payload


def _required(value: str | None, flag: str) -> str:
    """Return a command-line value, raising when this gate needs it and it is absent."""
    if not value:
        raise ValueError(f"{flag} is required for this gate")
    return value


def sweep_gate(config: Mapping[str, Any]) -> SweepGate:
    """Return the configured admission check the scheduled sweep re-runs."""
    section = _section(config, "sweep")
    values: dict[str, str] = {}
    for key, field in (("gate_check_run", "check_run"), ("gate_workflow_path", "workflow_path")):
        value = section.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"configuration key 'sweep.{key}' must be a non-empty string")
        values[field] = value
    return SweepGate(**values)


GATES = ("thread-finality", "platform-order", "platform-status", "queue-disposition", "merge-group-size", "sweep")


def main(argv: list[str] | None = None) -> int:
    """Evaluate one merge-admission gate against saved GitHub evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", choices=GATES)
    parser.add_argument("--snapshot", type=Path, help="saved evidence snapshot (all gates but merge-group-size)")
    parser.add_argument("--candidate-sha", help="exact merge candidate the snapshot must describe")
    parser.add_argument(
        "--platform-sha",
        help="merge-group commit whose platform run must also pass; defaults to the candidate",
    )
    parser.add_argument("--event-name", help="GitHub event that triggered this run (queue-disposition)")
    parser.add_argument("--compare", type=Path, help="saved REST compare base...head response (merge-group-size)")
    parser.add_argument("--base-sha", help="merge group base commit (merge-group-size)")
    parser.add_argument("--head-sha", help="merge group head commit (merge-group-size)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.gate == "merge-group-size":
            verdict = evaluate_merge_group_size(
                _load_json(args.compare, "--compare"),
                base_sha=_required(args.base_sha, "--base-sha"),
                head_sha=_required(args.head_sha, "--head-sha"),
                max_entries=_max_entries(config),
            )
        elif args.gate == "sweep":
            # One action per line and nothing at all when there is none: the
            # workflow treats a non-empty output file as work to do.
            verdict = "\n".join(sweep_actions(_load_json(args.snapshot, "--snapshot"), gate=sweep_gate(config)))
        elif args.gate == "queue-disposition":
            verdict = queue_disposition(
                _load_json(args.snapshot, "--snapshot"), event_name=_required(args.event_name, "--event-name")
            )
        else:
            payload = _load_json(args.snapshot, "--snapshot")
            candidate_sha = _required(args.candidate_sha, "--candidate-sha")
            if args.gate == "thread-finality":
                evaluate_thread_finality(
                    payload,
                    candidate_sha=candidate_sha,
                    review_producers=_string_list(_section(config, "thread_finality"), "review_producers"),
                )
                verdict = f"thread-finality: no live review threads on candidate {candidate_sha}"
            else:
                evaluator = platform_status if args.gate == "platform-status" else evaluate_platform_order
                verdict = evaluator(
                    payload,
                    candidate_sha=candidate_sha,
                    platform_sha=args.platform_sha or candidate_sha,
                    producer=platform_producer(config),
                    sensitive_paths=_string_list(_section(config, "platform_order"), "sensitive_paths"),
                )
    except (OSError, json.JSONDecodeError, yaml.YAMLError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    if verdict:
        print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
