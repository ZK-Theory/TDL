"""Controls for tools/check_bypass_merges.py (obs 2026-11-10-bypass-merge-skipped-a-red-suite-and-left-main-red)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import pytest  # noqa: E402
from check_bypass_merges import Bypass, audit, main, merging_pull, time_period  # noqa: E402

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


def test_the_window_picks_the_smallest_period_that_covers_it() -> None:
    assert [time_period(days) for days in (1, 2, 7, 8, 30)] == ["day", "week", "week", "month", "month"]


@pytest.mark.parametrize("days", [0, 31, 90])
def test_a_window_the_api_cannot_read_is_refused_not_cut(days: int, capsys: pytest.CaptureFixture[str]) -> None:
    """Negative control: time_period=month silently capped a longer window and still exited clean."""
    with pytest.raises(ValueError, match="between 1 and 30"):
        time_period(days)
    with pytest.raises(SystemExit) as exited:
        main(["--days", str(days)])

    assert exited.value.code == 2
    assert "between 1 and 30" in capsys.readouterr().err


def test_the_merging_pull_is_the_one_whose_merge_commit_is_the_sha() -> None:
    """Negative control: pulls[0] judged whichever pull request GitHub listed first."""
    sha = "23f8f737" + "0" * 32
    pulls = [
        {"number": 418, "merged_at": "2026-11-09T10:00:00Z", "merge_commit_sha": "f" * 40},
        {"number": 419, "merged_at": None, "merge_commit_sha": None},
        {"number": 420, "merged_at": MERGED, "merge_commit_sha": sha},
    ]

    assert merging_pull(pulls, sha)["number"] == 420
    assert merging_pull(pulls[:2], sha)["number"] == 418
    assert merging_pull(pulls[1:2], sha) is None


def test_timestamps_compare_as_times_not_strings() -> None:
    """Negative control: 09:30+01:00 is 08:30Z, before a 09:00Z merge, which a string comparison reads as after."""
    checks = {name: [("success", "2026-11-10T09:30:00.250+01:00")] for name in (*REQUIRED, "suite-verdict")}
    late = {name: [("success", "2026-11-10T10:00:01+01:00")] for name in (*REQUIRED, "suite-verdict")}

    assert audit([_bypass(merged_at="2026-11-10T09:00:00Z", checks=checks)], REQUIRED) == []
    assert len(audit([_bypass(merged_at="2026-11-10T09:00:00Z", checks=late)], REQUIRED)) == 3
