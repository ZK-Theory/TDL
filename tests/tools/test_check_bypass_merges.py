"""Controls for tools/check_bypass_merges.py (obs 2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from check_bypass_merges import Bypass, audit  # noqa: E402

REQUIRED = ("admission-controls", "merge-admission")
MERGED = "2026-11-10T09:04:21Z"
GREEN = {
    "admission-controls": [("success", "2026-11-10T08:42:44Z")],
    "merge-admission": [("success", "2026-11-10T08:39:33Z")],
    "suite-verdict": [("success", "2026-11-10T08:57:49Z")],
}


def _bypass(**changes) -> Bypass:
    base = {
        "after_sha": "23f8f737" + "0" * 32,
        "pushed_at": MERGED,
        "pr_number": 420,
        "merged_at": MERGED,
        "head_sha": "441f3f09" + "0" * 32,
        "texts": ("Bypass reason: a gate-file edit to .github/workflows/ci.yml.",),
        "checks": GREEN,
    }
    base.update(changes)
    return Bypass(**base)


def test_a_bypass_with_green_checks_and_a_reason_is_clean() -> None:
    assert audit([_bypass()], REQUIRED) == []


def test_the_420_merge_is_reported() -> None:
    """Negative control: #420's state at its merge (checks running, the suite red on the previous head, no reason)."""
    checks = {
        "admission-controls": [(None, None)],
        "merge-admission": [("success", "2026-11-10T09:05:44Z")],
        "suite-verdict": [("failure", "2026-11-10T08:57:49Z")],
    }

    problems = audit([_bypass(checks=checks, texts=("WP9.3-1 ...",))], REQUIRED)

    assert any("admission-controls was not green" in p for p in problems)
    assert any("merge-admission was not green" in p for p in problems), "a check that went green after the merge"
    assert any("suite-verdict was not green" in p for p in problems), "suite-verdict is required by the audit"
    assert any("no 'Bypass reason:' line" in p for p in problems)
    assert len(problems) == 4


def test_a_reason_in_a_comment_counts() -> None:
    assert audit([_bypass(texts=("no reason here", "**Bypass reason:** CODEOWNERS edit"))], REQUIRED) == []


def test_a_reason_must_say_something() -> None:
    assert audit([_bypass(texts=("Bypass reason:   ",))], REQUIRED) == [
        f"#420 23f8f737 ({MERGED}): bypass with no 'Bypass reason:' line in the pull request"
    ]


def test_a_bypass_with_no_pull_request_is_reported() -> None:
    problems = audit([_bypass(pr_number=None, merged_at=None, head_sha=None, texts=(), checks={})], REQUIRED)

    assert problems == [f"23f8f737 ({MERGED}): bypassed update to main with no pull request"]
