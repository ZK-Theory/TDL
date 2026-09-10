#!/usr/bin/env python3
# Research context: TDA-Research/03-Papers/P06/_project.md
# Purpose: fail merge admission closed when review-thread finality or
# platform-evidence ordering cannot be established at the exact merge candidate.
"""Merge-admission gates evaluated against a single evidence snapshot.

Two gates, both derived from recorded Gate 6 failures:

``thread-finality``
    Observation ``01M0PWSR73ABY48X8YW7KQX6Q6``. PR #262 merged 89 seconds after
    five Codex review threads were published; the clean-thread readback that
    admitted it was taken before those threads existed. Thread finality is a
    property of the exact merge candidate, so it is re-derived here from a
    snapshot bound to ``headRefOid`` and never carried forward.

``platform-order``
    Observation ``01M0Q0WXJSCX5WJ69H2G9DG4E3``. PR #263's first head was
    accepted on Windows-reachable controls while 13 decisive POSIX controls were
    skipped; the Linux workflow then failed. For candidates touching
    filesystem/concurrency surfaces the Linux job must be terminal and green
    before any approving review is submitted.

Both gates raise :class:`ValueError` on absent, malformed, or truncated
evidence: silent absence is the failure mode these gates exist to remove.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
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


def _changed_paths(pull_request: Mapping[str, Any]) -> list[str]:
    """Return the candidate's changed file paths."""
    nodes = _require_nodes(pull_request.get("files"), "pullRequest.files")
    paths: list[str] = []
    for index, node in enumerate(nodes):
        path = node.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"pullRequest.files.nodes[{index}].path is missing")
        paths.append(path)
    return paths


def _rollup_contexts(payload: Mapping[str, Any], platform_sha: str) -> list[Mapping[str, Any]]:
    """Return the status-check contexts recorded against the platform commit.

    The platform commit is the pull request head for ordinary events and the
    synthetic merge-group commit inside a merge queue. Binding the rollup to an
    explicit oid keeps the queue candidate from being certified by the pre-queue
    head's checks.
    """
    commit = _repository(payload).get("platformCommit")
    if commit is None:
        raise ValueError(f"snapshot carries no commit object for {platform_sha}; platform evidence is absent")
    commit = _require_mapping(commit, "response.data.repository.platformCommit")
    if commit.get("oid") != platform_sha:
        raise ValueError(f"platform commit {commit.get('oid')!r} is not {platform_sha!r}")
    rollup = commit.get("statusCheckRollup")
    if rollup is None:
        # No checks have registered on this commit yet. That is a legitimate
        # transient state, distinct from a failed query, so it is reported as
        # zero contexts and the caller decides whether to block or wait.
        return []
    return _require_nodes(_require_mapping(rollup, "statusCheckRollup").get("contexts"), "statusCheckRollup.contexts")


def _sensitive_paths_touched(pull_request: Mapping[str, Any], sensitive_paths: Sequence[str]) -> list[str]:
    """Return the candidate's changed paths that are platform-sensitive."""
    return sorted(path for path in _changed_paths(pull_request) if path_is_sensitive(path, sensitive_paths))


def _linux_check(payload: Mapping[str, Any], *, platform_sha: str, linux_check_run: str) -> Mapping[str, Any] | None:
    """Return the Linux check run on the platform commit, or ``None`` if absent.

    Raises:
        ValueError: If more than one check run carries the configured name,
            which makes "the" platform result ambiguous.
    """
    matches = [
        context
        for context in _rollup_contexts(payload, platform_sha)
        if context.get("__typename") == "CheckRun" and context.get("name") == linux_check_run
    ]
    if len(matches) > 1:
        raise ValueError(f"{len(matches)} check runs named {linux_check_run!r} on {platform_sha}; result is ambiguous")
    return matches[0] if matches else None


def platform_status(
    payload: Mapping[str, Any],
    *,
    candidate_sha: str,
    platform_sha: str,
    linux_check_run: str,
    sensitive_paths: Sequence[str],
) -> str:
    """Report whether the platform gate can be decided yet.

    ``pull_request: synchronize`` starts this gate alongside CI, so the Linux
    job is routinely queued or in progress when the first snapshot is taken. No
    event fires when it later completes, so failing at that moment would leave a
    permanently red check on a candidate that is actually fine. The caller waits
    on ``pending`` instead.

    Args:
        payload: Raw ``gh api graphql`` response for the pull request.
        candidate_sha: The exact merge candidate the evidence must describe.
        platform_sha: Commit whose checks carry the platform evidence.
        linux_check_run: Check-run name of the Linux-required job.
        sensitive_paths: Filesystem/concurrency path prefixes and globs.

    Returns:
        ``"not-applicable"``, ``"pending"``, or ``"ready"``.

    Raises:
        ValueError: If the evidence is stale, truncated, or malformed.
    """
    pull_request = _pull_request(payload)
    _assert_candidate(pull_request, candidate_sha)
    if not _sensitive_paths_touched(pull_request, sensitive_paths):
        return "not-applicable"
    linux = _linux_check(payload, platform_sha=platform_sha, linux_check_run=linux_check_run)
    if linux is None or linux.get("status") != "COMPLETED":
        return "pending"
    return "ready"


def _latest_approvals(pull_request: Mapping[str, Any], candidate_sha: str) -> dict[str, Mapping[str, Any]]:
    """Return each reviewer's most recent approval of the candidate.

    GitHub keeps every review record, so an approval submitted before the Linux
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
    linux_check_run: str,
    sensitive_paths: Sequence[str],
) -> str:
    """Require green Linux evidence before approval on platform-sensitive code.

    Args:
        payload: Raw ``gh api graphql`` response for the pull request.
        candidate_sha: The exact merge candidate the evidence must describe.
        platform_sha: Commit whose checks carry the platform evidence -- the
            pull request head ordinarily, the merge-group commit in a queue.
        linux_check_run: Check-run name of the Linux-required job.
        sensitive_paths: Filesystem/concurrency path prefixes and globs.

    Returns:
        A one-line human-readable verdict for the passing cases.

    Raises:
        ValueError: If the evidence is stale, truncated, or malformed; if the
            Linux job is absent, non-terminal, or failing on the platform
            commit; or if a reviewer's live approval of the candidate was
            submitted before that job concluded.
    """
    pull_request = _pull_request(payload)
    _assert_candidate(pull_request, candidate_sha)

    touched = _sensitive_paths_touched(pull_request, sensitive_paths)
    if not touched:
        return "platform-order: not applicable (no filesystem or concurrency paths changed)"

    linux = _linux_check(payload, platform_sha=platform_sha, linux_check_run=linux_check_run)
    if linux is None:
        raise ValueError(
            f"no {linux_check_run!r} check run on {platform_sha}; platform-sensitive paths changed: "
            + ", ".join(touched)
        )
    if linux.get("status") != "COMPLETED":
        raise ValueError(f"{linux_check_run} is {linux.get('status')!r} on {platform_sha}, not COMPLETED")
    if linux.get("conclusion") != "SUCCESS":
        raise ValueError(f"{linux_check_run} concluded {linux.get('conclusion')!r} on {platform_sha}, not SUCCESS")
    completed_at = _parse_timestamp(linux.get("completedAt"), f"{linux_check_run}.completedAt")

    early = []
    for login, review in _latest_approvals(pull_request, candidate_sha).items():
        if _parse_timestamp(review.get("submittedAt"), "review.submittedAt") <= completed_at:
            early.append(f"{login} at {review['submittedAt']}")
    if early:
        raise ValueError(
            f"approval preceded Linux evidence ({linux_check_run} completed {linux['completedAt']}): "
            + "; ".join(sorted(early))
            + "; re-request review against the Linux-green candidate"
        )
    return f"platform-order: {linux_check_run} green before approval; sensitive paths: {', '.join(touched)}"


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


def main(argv: list[str] | None = None) -> int:
    """Evaluate one merge-admission gate against a saved evidence snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", choices=("thread-finality", "platform-order", "platform-status"))
    parser.add_argument("--snapshot", type=Path, required=True, help="saved `gh api graphql` response")
    parser.add_argument("--candidate-sha", required=True, help="exact merge candidate the snapshot must describe")
    parser.add_argument(
        "--platform-sha",
        help="commit carrying the platform evidence; defaults to the candidate, differs inside a merge queue",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args(argv)
    platform_sha = args.platform_sha or args.candidate_sha

    try:
        payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("evidence snapshot must be a JSON object")
        config = load_config(args.config)
        if args.gate == "thread-finality":
            section = _section(config, "thread_finality")
            evaluate_thread_finality(
                payload,
                candidate_sha=args.candidate_sha,
                review_producers=_string_list(section, "review_producers"),
            )
            verdict = f"thread-finality: no live review threads on candidate {args.candidate_sha}"
        else:
            section = _section(config, "platform_order")
            linux_check_run = section.get("linux_check_run")
            if not isinstance(linux_check_run, str) or not linux_check_run:
                raise ValueError("configuration key 'linux_check_run' must be a non-empty string")
            evaluator = platform_status if args.gate == "platform-status" else evaluate_platform_order
            verdict = evaluator(
                payload,
                candidate_sha=args.candidate_sha,
                platform_sha=platform_sha,
                linux_check_run=linux_check_run,
                sensitive_paths=_string_list(section, "sensitive_paths"),
            )
    except (OSError, json.JSONDecodeError, yaml.YAMLError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
