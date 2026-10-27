# Research context: docs/plans/strategy/system-review-2026-10-27-decision-report.md (Groups B, D, E)
# Purpose: Negative and positive controls for the three lints the 2026-10-27 review campaign added:
# check_test_commit_literals, check_register_reachability and check_cited_decisions.
"""Controls for the 2026-10-27 review-campaign lints.

Each lint is shown to fire on the failure its observation records and to stay quiet on the compliant case:
obs 2026-10-24-squash-merge-strands-sha-pinned-controls, 2026-10-22-w11-owner-acceptance-stranded-on-unmerged-branch
and 2026-10-21-gate7-brief-restated-superseded-and-closed-items.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import check_cited_decisions  # noqa: E402
import check_register_reachability  # noqa: E402
import check_test_commit_literals  # noqa: E402

REGISTER = check_register_reachability.REGISTER


def _git(cwd: Path, *args: str) -> str:
    env_args = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null"]
    done = subprocess.run(["git", *env_args, *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    """A clone whose origin/main holds one commit; returns (clone, that commit)."""
    origin, clone = tmp_path / "origin.git", tmp_path / "clone"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "init", "-q", "-b", "main", str(clone))
    _git(clone, "remote", "add", "origin", str(origin))
    (clone / REGISTER).parent.mkdir(parents=True)
    (clone / REGISTER).write_text("# Register\n\n### P-001 — first decision recorded on main\n", encoding="utf-8")
    _git(clone, "add", ".")
    _git(clone, "commit", "-q", "-m", "base")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    return clone, _git(clone, "rev-parse", "HEAD")


def _branch_commit(clone: Path, branch: str, register_line: str | None = None) -> str:
    _git(clone, "switch", "-q", "-c", branch)
    if register_line:
        with (clone / REGISTER).open("a", encoding="utf-8") as fh:
            fh.write(register_line + "\n")
        _git(clone, "add", ".")
        _git(clone, "commit", "-q", "-m", branch)
    else:
        _git(clone, "commit", "-q", "--allow-empty", "-m", branch)
    sha = _git(clone, "rev-parse", "HEAD")
    _git(clone, "switch", "-q", "main")
    return sha


def _test_file(clone: Path, body: str) -> Path:
    tests = clone / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_fixture.py").write_text(body, encoding="utf-8")
    return tests


# --- check_test_commit_literals ----------------------------------------------------------------------------


def test_a_branch_only_commit_literal_fails(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    stranded = _branch_commit(clone, "pipe/branch-only")
    tests = _test_file(clone, f'WRONG_ANNEX = "{stranded}"\n')
    problems, _ = check_test_commit_literals.check(clone, tests)
    assert len(problems) == 1 and stranded[:12] in problems[0] and "squash merge strands it" in problems[0]


def test_a_commit_on_main_passes_and_a_synthetic_hash_is_not_judged(tmp_path: Path) -> None:
    clone, on_main = _repo(tmp_path)
    tests = _test_file(clone, f'BASE = "{on_main}"\nFAKE = "{"ab" * 20}"\n')
    problems, summary = check_test_commit_literals.check(clone, tests)
    assert problems == []
    assert "1 on main" in summary and "1 not a commit here" in summary


def test_a_marked_data_literal_passes_inline_or_on_the_line_above(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    stranded = _branch_commit(clone, "pipe/branch-only")
    tests = _test_file(
        clone,
        f'A = "{stranded}"  # commit-literal: data\n# commit-literal: data (compared as a string)\nB = "{stranded}"\n',
    )
    problems, summary = check_test_commit_literals.check(clone, tests)
    assert problems == [] and "1 data" in summary


def test_marking_one_occurrence_does_not_excuse_another(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    stranded = _branch_commit(clone, "pipe/branch-only")
    tests = _test_file(clone, f'A = "{stranded}"  # commit-literal: data\n\n\nB = "{stranded}"\n')
    problems, _ = check_test_commit_literals.check(clone, tests)
    assert len(problems) == 1 and "test_fixture.py:4" in problems[0]


def test_a_commit_on_a_remote_tag_passes(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    tagged = _branch_commit(clone, "review/tagged")
    _git(clone, "tag", "pin/review", tagged)
    _git(clone, "push", "-q", "origin", "pin/review")
    tests = _test_file(clone, f'REVIEW = "{tagged}"\n')
    problems, summary = check_test_commit_literals.check(clone, tests)
    assert problems == [] and "1 tagged" in summary


# --- check_register_reachability ---------------------------------------------------------------------------

_DECISION = "On 2026-08-01 Stephen accepted the exact revision for limb 1 of this decision."


def test_register_text_only_on_a_branch_is_reported(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    tip = _branch_commit(clone, "codex/acceptance-record", _DECISION)
    problems, summary = check_register_reachability.check(clone, open_prs={})
    assert len(problems) == 1 and tip[:8] in problems[0] and "0/1 added lines" in problems[0]
    assert "1 stranded" in summary


def test_register_text_already_on_main_by_squash_is_not_reported(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    _branch_commit(clone, "docs/squashed", _DECISION)
    with (clone / REGISTER).open("a", encoding="utf-8") as fh:
        fh.write(_DECISION + "\n")
    _git(clone, "commit", "-q", "-am", "squash of docs/squashed")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    problems, summary = check_register_reachability.check(clone, open_prs={})
    assert problems == [] and "0 stranded" in summary


def test_a_branch_carried_by_an_open_pr_is_pending_not_stranded(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    tip = _branch_commit(clone, "docs/landing", _DECISION)
    problems, summary = check_register_reachability.check(clone, open_prs={"other-name": (398, tip)})
    assert problems == [] and "pending in open PRs" in summary and "open PR #398" in summary


def test_a_merge_queue_ref_is_ignored(tmp_path: Path) -> None:
    clone, _ = _repo(tmp_path)
    _branch_commit(clone, "gh-readonly-queue/main/pr-1-abc", _DECISION)
    problems, _ = check_register_reachability.check(clone, open_prs={})
    assert problems == []


# --- check_cited_decisions ---------------------------------------------------------------------------------

_REGISTER_TEXT = """### P-033 — Full live capability before R2 dispatch

**Status:** Accepted

### P-035 — First-release sequence

**Status:** Accepted

### P-042 — Owner-operated sessions

**Supersedes:** P-033 and the active first-release sequence in P-035; amends P-029
**Status:** Accepted
"""


def test_a_superseded_citation_fails_and_naming_the_successor_passes(tmp_path: Path) -> None:
    brief = tmp_path / "brief.md"
    brief.write_text("Does P-033 bind Gate 7 compute?\nP-033 (superseded by P-042) is history.\n", encoding="utf-8")
    problems, _ = check_cited_decisions.check([brief], _REGISTER_TEXT)
    assert problems == [f"{brief}:1: cites P-033, which P-042 supersedes"]


def test_an_amendment_clause_inside_supersedes_is_a_note_not_a_failure(tmp_path: Path) -> None:
    brief = tmp_path / "brief.md"
    brief.write_text("P-029 still sets the budget.\n", encoding="utf-8")
    problems, notes = check_cited_decisions.check([brief], _REGISTER_TEXT)
    assert problems == [] and notes == [f"{brief}:1: cites P-029, which P-042 amends"]
