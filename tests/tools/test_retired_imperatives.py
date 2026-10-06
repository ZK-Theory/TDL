"""Binding tests for the retirement gate (obs 2026-08-22-retired-procedure-kept-live-imperatives).

The gate's whole justification is that a banner does not neutralise imperatives, and
that three authors in a row added a banner anyway. So the controls here are written
around one question: *would this have failed on PR #271?* The first negative control is
literally that shape -- a header banner announcing supersession over an unquoted body --
and it must fail.

Every negative control asserts a specific rule id, not merely "some finding". A gate
that fires for the wrong reason is a gate that will be silenced for the wrong reason.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_retired_imperatives import DEFAULT_ROOTS, check_document, scan


REPO_ROOT = Path(__file__).resolve().parents[2]


def _rules(text: str, path: str = "docs/plans/x/doc.md") -> list[str]:
    return [finding.rule for finding in check_document(path, text)]


PR271_SHAPE = """# 06q — Gate 6 Recovery and Closure Plan

> **SUPERSEDED — 2026-09-05:** Stephen approved the revised 06s delivery plan. The text
> below is historical, including its sole-authority and no-successor instructions.

**Date:** 2026-08-22

## 4. Sequential implementation slices

Each slice is a latest-main PR. Do not cherry-pick PR #260 wholesale. Keep the existing
six Jira jobs and read back both dependency directions after the amendment merges.
"""


# --------------------------------------------------------------------------------------
# Positive application: the live tree.
# --------------------------------------------------------------------------------------


def test_repository_plans_satisfy_the_retirement_gate():
    """Every scanned plan either makes no retirement claim or declares and quotes its scope."""
    findings = scan(DEFAULT_ROOTS, REPO_ROOT)
    assert findings == [], "retirement gate findings:\n" + "\n".join(f.render() for f in findings)


# --------------------------------------------------------------------------------------
# The contract-bound test. Deliberately asserts both halves in one function: that the
# live tree is clean, AND that the gate fires on the shapes it exists to catch. A
# clean-tree assertion on its own is satisfied equally well by a gate that can never
# fail, which is the failure mode this repository has already paid for once -- the
# contract validator sat in .git/hooks for 47 days reporting nothing while never running.
# --------------------------------------------------------------------------------------


def test_retirement_gate_is_enforced_and_demonstrably_fires():
    live = scan(DEFAULT_ROOTS, REPO_ROOT)
    assert not live, "retirement gate findings:\n" + "\n".join(f.render() for f in live)

    must_fire = {
        "banner over unquoted body (the PR #271 shape)": (PR271_SHAPE, "R1-declaration"),
        "unquoted line inside a declared retired span": (
            '# P\n\n**Status:** SUPERSEDED.\n\n<!-- retirement-scope:\nretired:\n  - "## A"\n-->\n\n'
            "## A\n\nUnquoted instruction.\n",
            "R2-unquoted",
        ),
        "empty scope with no justifying note": (
            "# P\n\n**Status:** RETIRED.\n\n<!-- retirement-scope:\nretired: []\n-->\n\n## A\n\nProse.\n",
            "R1-declaration",
        ),
        "declaration pointing at a heading that no longer exists": (
            '# P\n\n**Status:** SUPERSEDED.\n\n<!-- retirement-scope:\nretired:\n  - "## Gone"\n-->\n\n'
            "## A\n\n> quoted\n",
            "R2-scope",
        ),
    }
    for label, (text, expected_rule) in must_fire.items():
        rules = _rules(text)
        assert rules != [], f"gate stayed silent on {label!r} -- it cannot fire on this shape"
        assert expected_rule in rules, f"gate fired on {label!r} for the wrong reason; rules={rules}"

    must_not_fire = {
        "active successor preserving others' retired evidence": (
            "# 06s\n\n**Supersedes:** 06q.\n**Preserves:** retired evidence branches.\n\n"
            "## 1\n\nRun the packet and record the SHA.\n"
        ),
        "supersession discussed only in the body": ("# P\n\n**Date:** x\n\n## 1\n\n06r is superseded. Do the work.\n"),
    }
    for label, text in must_not_fire.items():
        rules = _rules(text)
        assert not rules, f"gate produced a false positive on {label!r}; rules={rules}"


# --------------------------------------------------------------------------------------
# Negative controls. Each of these MUST fail; a green run here means the gate is vacuous.
# --------------------------------------------------------------------------------------


def test_banner_over_unquoted_body_fails_which_is_the_pr271_shape():
    """The exact configuration that shipped three times: a banner, and nothing else."""
    assert "R1-declaration" in _rules(PR271_SHAPE)


def test_declared_retired_span_with_unquoted_prose_fails():
    text = """# Plan

**Status:** SUPERSEDED by the successor plan.

<!-- retirement-scope:
retired:
  - "## 2. Slices"
-->

## 1. Live section

Ordinary live prose that must not be touched.

## 2. Slices

> This line is properly quoted.
This line is not, and it reads as a live instruction.
"""
    findings = check_document("docs/plans/x/doc.md", text)
    assert [f.rule for f in findings] == ["R2-unquoted"]
    assert findings[0].line == text.split("\n").index("This line is not, and it reads as a live instruction.") + 1


def test_empty_scope_without_a_note_fails_so_the_escape_hatch_costs_something():
    text = """# Plan

**Status:** RETIRED as an active authority.

<!-- retirement-scope:
retired: []
-->

## 1. Body

Unquoted prose.
"""
    assert _rules(text) == ["R1-declaration"]


def test_declaration_naming_a_missing_heading_fails_loudly():
    """A renamed heading must not silently empty the declared scope."""
    text = """# Plan

**Status:** SUPERSEDED.

<!-- retirement-scope:
retired:
  - "## 4. Heading that was renamed away"
-->

## 4. Sequential implementation slices

Unquoted prose.
"""
    findings = check_document("docs/plans/x/doc.md", text)
    assert [f.rule for f in findings] == ["R2-scope"]
    assert "no heading in this document matches" in findings[0].message


def test_ambiguous_heading_label_fails():
    text = """# Plan

**Status:** SUPERSEDED.

<!-- retirement-scope:
retired:
  - "## Step"
-->

## Step

> quoted

## Step

> quoted
"""
    findings = check_document("docs/plans/x/doc.md", text)
    assert [f.rule for f in findings] == ["R2-scope"]
    assert "matches 2 headings" in findings[0].message


def test_retained_label_outside_any_retired_span_fails():
    """A stale carve-out is a declaration that has drifted from the document."""
    text = """# Plan

**Status:** SUPERSEDED.

<!-- retirement-scope:
retired:
  - "## 2. Retired"
retained:
  - "## 3. Elsewhere"
-->

## 2. Retired

> quoted

## 3. Elsewhere

Live prose.
"""
    findings = check_document("docs/plans/x/doc.md", text)
    assert [f.rule for f in findings] == ["R2-scope"]
    assert "carves out nothing" in findings[0].message


@pytest.mark.parametrize(
    "body",
    [
        "retired: [",  # malformed YAML
        "retired:\n  - '## A'\nunexpected_key: true",
    ],
)
def test_malformed_declarations_fail(body: str):
    text = f"# Plan\n\n**Status:** SUPERSEDED.\n\n<!-- retirement-scope:\n{body}\n-->\n\n## A\n\n> quoted\n"
    assert _rules(text) == ["R1-declaration"]


# --------------------------------------------------------------------------------------
# Must-pass controls. A gate that fires on live documents gets switched off.
# --------------------------------------------------------------------------------------


def test_active_successor_describing_others_retired_evidence_is_not_captured():
    """The 06s shape.

    06s is the live plan; its header preserves "retired evidence branches" belonging to
    other objects. An unrestricted header scan flagged it, which would have made the
    gate's first act a false accusation against the only active plan in the directory.
    """
    text = """# 06s — Gate 6 Delivery Replan

**Date:** 2026-09-05
**Supersedes:** 06q as the active delivery plan.
**Preserves:** the historical real run, merged STORE implementation, retired evidence
branches, and the live control store.

## 1. Position

Live prose with instructions: run the packet and record the SHA.
"""
    assert _rules(text) == []


def test_body_mention_of_supersession_is_not_a_self_claim():
    text = """# Plan

**Date:** 2026-09-05

## 1. Context

PR #260 is retired unmerged; 06r is superseded for active execution.
Do the work described below.
"""
    assert _rules(text) == []


def test_quoted_span_with_an_unquoted_retained_carve_out_passes():
    """Retirement is per-claim: a successor may keep a sub-span as reference material."""
    text = """# Plan

**Status:** SUPERSEDED as a delivery authority.

<!-- retirement-scope:
retired:
  - "## 4. Slices"
retained:
  - "### Step 5"
-->

## 4. Slices

> ### Step 0
>
> Do not cherry-pick. Read back both directions.

### Step 5

The successor still cites this action table, so it stays readable.

> ### Step 6
>
> Retired construction sequence.
"""
    assert _rules(text) == []


def test_fenced_code_inside_a_retired_span_need_not_be_quoted():
    text = """# Plan

**Status:** SUPERSEDED.

<!-- retirement-scope:
retired:
  - "## 2. Retired"
-->

## 2. Retired

> Historical narrative.

```bash
ars store repair-binding --help
```
"""
    assert _rules(text) == []


def test_whole_body_scope_requires_the_whole_body_quoted():
    retired_ok = """# Plan (retired historical evidence)

**Status:** RETIRED.

<!-- retirement-scope:
retired:
  - "*"
note: retained in full as evidence.
-->

## 1. Findings

> Everything here is quoted.
"""
    assert _rules(retired_ok) == []

    leaked = retired_ok.replace("> Everything here is quoted.", "Everything here is quoted.")
    assert _rules(leaked) == ["R2-unquoted"]
