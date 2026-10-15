#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-10-15-decision-report.md (Group B)
# Purpose: Say at session start when the weekly system review is overdue, so a skipped review is a printed
# line in every session instead of something one session might notice by reading a date file.
"""Print one line saying how old the last weekly system review is.

Obs 2026-10-15-weekly-review-missed-its-run-without-signal: the scheduled review did not run on 2026-10-13,
and the gap was noticed only because a session happened to read ``last-review-date.txt`` under a CLAUDE.md
instruction. The review audits every gate's liveness, so it needs a liveness signal of its own.

``--session-start`` always exits 0: SessionStart must never block a session. Without it, an overdue or
unreadable date exits 1, for scripted callers.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

DEFAULT_FILE = Path.home() / ".claude" / "skill-observations" / "last-review-date.txt"
# Weekly cadence plus one day of slack for a late scheduled run.
MAX_AGE_DAYS = 8


def verdict(date_file: Path, today: date, max_age_days: int = MAX_AGE_DAYS) -> tuple[bool, str]:
    """Return (current, one-line message) for the review date recorded in ``date_file``."""
    try:
        raw = date_file.read_text(encoding="utf-8").strip()
    except OSError:
        return False, f"WARNING: no system review date recorded at {date_file}; run the research-observer review"
    try:
        last = date.fromisoformat(raw)
    except ValueError:
        return False, f"WARNING: unreadable system review date {raw[:40]!r} in {date_file}"
    age = (today - last).days
    if age > max_age_days:
        return False, (
            f"WARNING: the weekly system review last ran {last.isoformat()}, {age} days ago (limit {max_age_days}); "
            "it is overdue: run the research-observer System Review"
        )
    return True, f"OK: the weekly system review last ran {last.isoformat()} ({age} days ago)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--date-file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--today", type=date.fromisoformat, default=None, help="For tests: today's date.")
    parser.add_argument("--max-age-days", type=int, default=MAX_AGE_DAYS)
    parser.add_argument("--session-start", action="store_true", help="Always exit 0.")
    args = parser.parse_args(argv)
    current, message = verdict(args.date_file, args.today or date.today(), args.max_age_days)
    # ASCII only: a SessionStart hook's stdout goes through the Windows console code page.
    print(message.encode("ascii", "replace").decode("ascii"))
    return 0 if current or args.session_start else 1


if __name__ == "__main__":
    raise SystemExit(main())
