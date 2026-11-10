"""Controls for tools/nightly_issue_policy.py (obs 2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from nightly_issue_policy import decide  # noqa: E402

NOW = "2026-11-10T08:00:00Z"
ISSUE_413 = {"number": 413, "state": "CLOSED", "createdAt": "2026-11-03T09:54:45Z"}


def test_the_first_red_night_opens_an_issue() -> None:
    assert decide("failure", NOW, []) == {"action": "create", "number": None, "note": ""}


def test_a_red_night_with_an_open_issue_comments() -> None:
    assert decide("failure", NOW, [{"number": 414, "state": "OPEN", "createdAt": "2026-11-08T09:03:55Z"}])[
        "action"
    ] == ("comment")


def test_a_single_red_episode_closes_on_green() -> None:
    issues = [{"number": 414, "state": "OPEN", "createdAt": "2026-11-08T09:03:55Z"}]

    assert decide("success", NOW, issues) == {"action": "close", "number": 414, "note": ""}


def test_a_second_red_episode_in_the_window_stays_open() -> None:
    """Negative control: #413 and #414, five days apart, both closed themselves; the second must not."""
    issues = [ISSUE_413, {"number": 414, "state": "OPEN", "createdAt": "2026-11-08T09:03:55Z"}]

    decision = decide("success", NOW, issues)

    assert decision["action"] == "keep-open"
    assert decision["number"] == 414
    assert "#413, #414" in decision["note"]


def test_a_new_red_episode_names_the_earlier_ones() -> None:
    assert "#413" in decide("failure", NOW, [ISSUE_413])["note"]


def test_episodes_older_than_the_window_do_not_count() -> None:
    issues = [
        {"number": 300, "state": "CLOSED", "createdAt": "2026-10-01T08:00:00Z"},
        {"number": 414, "state": "OPEN", "createdAt": "2026-11-08T09:03:55Z"},
    ]

    assert decide("success", NOW, issues)["action"] == "close"


def test_a_green_night_with_no_open_issue_does_nothing() -> None:
    assert decide("success", NOW, [ISSUE_413])["action"] == "none"
