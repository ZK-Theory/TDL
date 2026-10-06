# Research context: docs/plans/strategy/system-review-2026-09-29-decision-report.md (Campaign R)
# Purpose: Controls that the round-3 skill follow-ups from PR #307 are present in the authoring
# copy of each governing skill and mirrored byte-for-byte into the Claude Code tree.
"""Presence controls for the PR #307 follow-up rules.

Skill prose has no behaviour to execute, so the control is that each rule is in the authoring
copy (``.agents/skills``), is carried into the mirror (``.claude/skills``), and names its own
discriminating phrase. A rule that exists only in a review comment is not a rule.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

RULES = [
    (
        "using-git-worktrees-extras",
        "That\n  fallback is gated on the lock matching.",
        "the main-venv fallback is gated on the candidate's lock matching",
    ),
    (
        "contract-first-tdd",
        "a row for every generated or contract-defined field",
        "the correspondence table has a row for every generated or contract-defined field",
    ),
    (
        "contract-first-tdd",
        "names the test group and a nonzero executed count",
        "red evidence names the test group and a nonzero executed count",
    ),
    (
        "contract-first-tdd",
        "- [ ] Correspondence table: one row per generated or contract-defined field",
        "the completion checklist carries the correspondence-table item",
    ),
    (
        "contract-first-tdd",
        "- [ ] Each red run's evidence names its test group",
        "the completion checklist carries the red-evidence item",
    ),
    (
        "contract-first-tdd",
        "## Self-test before handing back",
        "the skill carries a self-test prompt for the admission and red-run rules",
    ),
]


def _normal(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.parametrize(("skill", "phrase", "rule"), RULES, ids=[r[2] for r in RULES])
def test_each_follow_up_rule_is_in_the_authoring_copy_and_the_mirror(skill: str, phrase: str, rule: str) -> None:
    for tree in (".agents", ".claude"):
        text = (ROOT / tree / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert _normal(phrase) in _normal(text), f"{rule}: missing from {tree}/skills/{skill}/SKILL.md"
