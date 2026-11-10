#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-11-10-decision-report.md (Group B, item 3)
# Purpose: Decide what the nightly suite's verdict job does with its red-nightly issue, keeping a recurring red visible.
"""Decide the red-nightly issue action for one scheduled research-system-suite run.

Obs 2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged: an intermittent writer-lock conflict turned
the nightly red on 2026-11-03 and 2026-11-08. Each night opened an issue (#413, #414) and the next green night closed
it, so nothing recorded that the same failure kept coming back.

Rules. The open issue is the newest open one with the red-nightly title, whatever its age; red episodes are counted
over the issues opened in the last ``WINDOW_DAYS`` days:

* red night, an issue open: comment on it;
* red night, none open: open one, saying how many red nights the window already holds;
* green night, an issue open, and it is the only red episode in the window: close it;
* green night, an issue open, and the window holds two or more red episodes: leave it open and say so, so a person
  triages the recurrence and closes it;
* green night, and the open issue predates the window: do nothing. It was left open for triage, or it has been red
  for longer than the window; either way a person closes it, and a nightly comment would only repeat itself.

Reads ``{"suite": ..., "now": ..., "issues": [{"number", "state", "createdAt"}]}`` as JSON on stdin and prints
``{"action": "comment"|"create"|"close"|"keep-open"|"none", "number": ..., "note": ...}``.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any

WINDOW_DAYS = 14


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def decide(suite: str, now: str, issues: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Return the action for this run; see the module docstring for the rules."""
    cutoff = _when(now) - timedelta(days=WINDOW_DAYS)
    issues = sorted(issues, key=lambda issue: _when(issue["createdAt"]))
    recent = [issue for issue in issues if _when(issue["createdAt"]) >= cutoff]
    # The open issue is chosen from every matching issue, not only the window: an issue left open for triage, or one
    # red for longer than the window, would otherwise drop out and the next red night would open a duplicate.
    opened = [issue for issue in issues if issue["state"].upper() == "OPEN"]
    current = opened[-1] if opened else None
    numbers = ", ".join(f"#{issue['number']}" for issue in recent)
    if suite != "success":
        if current is not None:
            return {"action": "comment", "number": current["number"], "note": ""}
        earlier = f" Earlier red episodes in the last {WINDOW_DAYS} days: {numbers}." if recent else ""
        return {"action": "create", "number": None, "note": earlier}
    if current is None:
        return {"action": "none", "number": None, "note": ""}
    if _when(current["createdAt"]) < cutoff:
        note = (
            f"#{current['number']} predates the {WINDOW_DAYS}-day window: it was left open for triage or has been red "
            "for longer than the window. A person closes it."
        )
        return {"action": "none", "number": current["number"], "note": note}
    if len(recent) >= 2:
        note = (
            f"Green tonight, but this is red episode {len(recent)} in {WINDOW_DAYS} days ({numbers}). "
            "Left open: a person triages the recurrence and closes this."
        )
        return {"action": "keep-open", "number": current["number"], "note": note}
    return {"action": "close", "number": current["number"], "note": ""}


def main() -> int:
    """Read one run's suite result and the matching issues as JSON on stdin and print the decision as JSON.

    Returns:
        0 always; the workflow acts on the printed ``action``.
    """
    data = json.load(sys.stdin)
    print(json.dumps(decide(data["suite"], data["now"], data["issues"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
