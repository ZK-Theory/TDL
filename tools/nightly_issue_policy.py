#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-11-10-decision-report.md (Group B, item 3)
# Purpose: Decide what the nightly suite's verdict job does with its red-nightly issue, keeping a recurring red visible.
"""Decide the red-nightly issue action for one scheduled research-system-suite run.

Obs 2026-11-10-nightly-writer-lock-flake-closes-its-own-issue-untriaged: an intermittent writer-lock conflict turned
the nightly red on 2026-11-03 and 2026-11-08. Each night opened an issue (#413, #414) and the next green night closed
it, so nothing recorded that the same failure kept coming back.

Rules, over the issues with the red-nightly title opened in the last ``WINDOW_DAYS`` days:

* red night, an issue open: comment on it;
* red night, none open: open one, saying how many red nights the window already holds;
* green night, an issue open, and it is the only red episode in the window: close it;
* green night, an issue open, and the window holds two or more red episodes: leave it open and say so, so a person
  triages the recurrence and closes it.

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
    recent = sorted(
        (issue for issue in issues if _when(issue["createdAt"]) >= cutoff), key=lambda issue: issue["createdAt"]
    )
    opened = [issue for issue in recent if issue["state"].upper() == "OPEN"]
    current = opened[-1]["number"] if opened else None
    numbers = ", ".join(f"#{issue['number']}" for issue in recent)
    if suite != "success":
        if current is not None:
            return {"action": "comment", "number": current, "note": ""}
        earlier = f" Earlier red episodes in the last {WINDOW_DAYS} days: {numbers}." if recent else ""
        return {"action": "create", "number": None, "note": earlier}
    if current is None:
        return {"action": "none", "number": None, "note": ""}
    if len(recent) >= 2:
        note = (
            f"Green tonight, but this is red episode {len(recent)} in {WINDOW_DAYS} days ({numbers}). "
            "Left open: a person triages the recurrence and closes this."
        )
        return {"action": "keep-open", "number": current, "note": note}
    return {"action": "close", "number": current, "note": ""}


def main() -> int:
    data = json.load(sys.stdin)
    print(json.dumps(decide(data["suite"], data["now"], data["issues"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
