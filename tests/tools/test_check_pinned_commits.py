# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group A)
# Purpose: Controls for tools/check_pinned_commits.py and tools/commit_reachability.py: a pinned commit on a
# local-only branch or local-only tag fails, the same commit published by a branch or a remote tag passes.
"""Controls for the pinned-commit check.

Obs 2026-10-15-accepted-contracts-pin-commits-on-local-only-branches: accepted contracts pinned five review
commits that existed only on local branches; the nightly CI clone failed 12 tests and nothing named the cause.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "check_pinned_commits.py"
sys.path.insert(0, str(REPO_ROOT / "tools"))
from commit_reachability import Publication  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    env_args = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null"]
    done = subprocess.run(["git", *env_args, *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _clone(tmp_path: Path) -> tuple[Path, str, str]:
    """A clone with one commit pushed to its origin's main and one only on a local branch."""
    origin, clone = tmp_path / "origin.git", tmp_path / "clone"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "init", "-q", "-b", "main", str(clone))
    _git(clone, "remote", "add", "origin", str(origin))
    _git(clone, "commit", "-q", "--allow-empty", "-m", "pushed")
    pushed = _git(clone, "rev-parse", "HEAD")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    _git(clone, "switch", "-q", "-c", "review/local-only")
    _git(clone, "commit", "-q", "--allow-empty", "-m", "review")
    stranded = _git(clone, "rev-parse", "HEAD")
    _git(clone, "switch", "-q", "main")
    return clone, pushed, stranded


def _pin(clone: Path, sha: str, name: str = "contract.yaml") -> Path:
    root = clone / ".research-system"
    root.mkdir(exist_ok=True)
    (root / name).write_text(f"review_commit: {sha}\n", encoding="utf-8")
    return root


def _run(clone: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), "--repo", str(clone)], capture_output=True, text=True, check=False
    )


@pytest.fixture(autouse=True)
def _not_in_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    # Outside GitHub Actions local tags are never trusted; the controls must not depend on where they run.
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


def test_a_commit_pinned_from_a_local_only_branch_fails(tmp_path: Path) -> None:
    clone, _, stranded = _clone(tmp_path)
    _pin(clone, stranded)
    result = _run(clone)
    assert result.returncode == 1
    assert (
        f"{stranded[:12]} (pinned in .research-system/contract.yaml) is a commit on no remote branch" in result.stderr
    )


def test_a_commit_on_the_remote_branch_passes(tmp_path: Path) -> None:
    clone, pushed, _ = _clone(tmp_path)
    _pin(clone, pushed)
    result = _run(clone)
    assert result.returncode == 0, result.stderr
    assert "1 commit(s) published-checked" in result.stdout


def test_a_local_tag_does_not_publish_but_a_pushed_tag_does(tmp_path: Path) -> None:
    clone, _, stranded = _clone(tmp_path)
    _pin(clone, stranded)
    _git(clone, "tag", "pin/review", stranded)
    assert _run(clone).returncode == 1, "a tag only this machine has is as stranded as a local branch"
    _git(clone, "push", "-q", "origin", "pin/review")
    result = _run(clone)
    assert result.returncode == 0, result.stderr
    assert Publication(clone).published_by(stranded) == "refs/tags/pin/review"


def test_an_id_absent_from_the_checkout_fails_unless_declared_foreign(tmp_path: Path) -> None:
    """The CI symptom: a clean clone without the object cannot verify the record, so the check must not pass."""
    clone, _, _ = _clone(tmp_path)
    missing = "0123456789abcdef0123456789abcdef01234567"
    _pin(clone, missing)
    result = _run(clone)
    assert result.returncode == 1
    assert (
        f"{missing[:12]} (pinned in .research-system/contract.yaml) is not an object in this checkout" in result.stderr
    )

    foreign = "145efcde673f1a1897eff250b77221d26c34c479"
    _pin(clone, foreign)
    result = _run(clone)
    assert result.returncode == 0, result.stderr
    assert "1 foreign" in result.stdout


def test_blob_pins_present_in_the_checkout_pass(tmp_path: Path) -> None:
    clone, _, _ = _clone(tmp_path)
    (clone / "skill.md").write_text("pinned bytes\n", encoding="utf-8")
    blob = _git(clone, "hash-object", "-w", "skill.md")
    _pin(clone, blob)
    result = _run(clone)
    assert result.returncode == 0, result.stderr
    assert "1 tree/blob(s) present" in result.stdout


def test_a_squash_merged_pr_head_counts_for_the_log_but_not_for_a_pin(tmp_path: Path) -> None:
    """Obs 2026-10-17-squash-merge-strands-the-pr-commits-entries-cite.

    GitHub keeps a deleted PR branch's head as refs/pull/<n>/head. For the observation log that is delivery.
    For a pinned record it is not: a CI clone (fetch-depth: 0) fetches branches and tags, never refs/pull/*.
    """
    clone, _, stranded = _clone(tmp_path)
    origin = tmp_path / "origin.git"
    _git(clone, "push", "-q", "origin", f"{stranded}:refs/pull/7/head")
    assert Publication(clone).published_by(stranded) == "refs/pull/7/head"
    assert Publication(clone, accept_pull_refs=False).published_by(stranded) is None
    _pin(clone, stranded)
    assert _run(clone).returncode == 1, "a pin on a PR-only commit is still unverifiable from a CI clone"
    assert origin.is_dir()


def test_a_commit_inside_a_merged_pr_counts_only_through_the_lookup(tmp_path: Path) -> None:
    """A squash-merged PR's intermediate commit is no PR head; GitHub's commit-to-PR association finds it."""
    clone, _, first = _clone(tmp_path)
    _git(clone, "switch", "-q", "review/local-only")
    _git(clone, "commit", "-q", "--allow-empty", "-m", "second")
    head = _git(clone, "rev-parse", "HEAD")
    _git(clone, "push", "-q", "origin", f"{head}:refs/pull/8/head")
    assert Publication(clone).published_by(first) is None, "an intermediate commit is not a PR head"
    found = Publication(clone, pulls_lookup=lambda _repo, sha: 8 if sha == first else None)
    assert found.published_by(first) == "merged PR #8"
    nowhere = Publication(clone, pulls_lookup=lambda _repo, _sha: None)
    assert nowhere.published_by(first) is None, "negative control: no branch, tag, PR head or merged PR"


def test_the_live_repository_pins_are_published() -> None:
    """Every id pinned under this repository's .research-system/ is published or declared foreign."""
    if (REPO_ROOT / ".git" / "shallow").is_file():
        pytest.fail("this check needs the remote's full history and tags; check out with fetch-depth: 0")
    result = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert " 0 problem(s)" in result.stdout
