# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §9.1, §17)
# Purpose: the grant fence refuses a paused W11 submit on predecessor code, which has no in-lock binding recheck.
"""The grant fence, on the predecessor's own code (WP9.3 note §9.1, §17 "Pin release by binding advance").

The predecessor is the base commit of WP9.3-1 (``2d9aeddc``, PR #411's merge), an ancestor of ``origin/main``. Its
``research_system``, ``tests`` and ``.research-system`` trees are extracted from Git under ``tmp_path`` (no worktree is
added to the repository), and a wrapper runs that unchanged package in a subprocess. A W11 submit admitted on a grant
is paused before its writer lock; the grant is then revoked, or expires, or stays live. On resume the predecessor's
runtime resolves the grant under its lock from a fresh replay, so a revoked or expired grant refuses with no append,
and a live one appends: the fence, not anything else, is what refuses.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PREDECESSOR_COMMIT = "2d9aeddc4c92646a8c65bf1895c867d9356b2f2d"
WRAPPER = Path(__file__).with_name("w9_grant_fence_wrapper.py")


@pytest.fixture(scope="module")
def predecessor(tmp_path_factory: pytest.TempPathFactory) -> Path:
    commit = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--verify", f"{PREDECESSOR_COMMIT}^{{commit}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", commit, "origin/main"], check=True)
    root = tmp_path_factory.mktemp("predecessor")
    archive = root / "predecessor.tar"
    subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "archive",
            "--format=tar",
            f"--output={archive}",
            commit,
            "research_system",
            "tests",
            ".research-system",
        ],
        check=True,
    )
    tree = root / "tree"
    with tarfile.open(archive) as extracted:
        extracted.extractall(tree, filter="data")
    return tree


def _run(predecessor: Path, tmp_path: Path, mode: str) -> dict[str, object]:
    work = tmp_path / mode
    work.mkdir()
    completed = subprocess.run(
        [sys.executable, str(WRAPPER), str(predecessor), str(work), mode],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(work),
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(
    ("mode", "message"),
    [("revoked", "authority grant revoked"), ("expired", "authority grant expired")],
)
def test_a_paused_w11_submit_on_predecessor_code_is_refused_by_the_grant_fence(
    predecessor: Path, tmp_path: Path, mode: str, message: str
) -> None:
    result = _run(predecessor, tmp_path, mode)
    assert str(result["package"]).startswith(str(predecessor.resolve()))
    assert message in str(result.get("error")), result
    assert result["appended"] == 0 and result["ledger_identical"] is True


def test_the_same_submit_with_its_grant_left_live_appends(predecessor: Path, tmp_path: Path) -> None:
    result = _run(predecessor, tmp_path, "live")
    assert result.get("status") == "accepted", result
    assert result["appended"] == 1
