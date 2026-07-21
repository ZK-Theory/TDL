# Proposal: a merge-seam test-suite gate

**Status:** PROPOSAL — awaiting Stephen's approval (CI/branch-protection change; not self-applied)
**Date:** 2026-07-21 · **Source:** weekly system review, skill-observation 84
**Owner decision required:** yes (repo settings / CI)

## Problem

Two PRs, each individually reviewed and green, both touched one function and
**composed into red tests on `main`** (obs 84). Neither PR was wrong in
isolation; the failure lived in their composition, and **no gate runs the test
suite against the actual post-merge tree**. Per-PR CI green is not the same as
`main`-stays-green: a PR is tested against its own branch, not against the tree
that results after the *other* PR merged.

This is the "no re-validation trigger at the seam" failure mechanism: each side
was validated once, in isolation, and the seam had no watched failure.

## Proposed mechanism (options — owner picks)

**Option A — require branches up to date before merge (lightest).**
Enable GitHub branch protection "Require branches to be up to date before
merging" on `main`. This forces each PR to re-run CI against `main`'s current
tip before it can merge, so the second PR is tested against the first's merged
state. Cheap, no new CI, but serializes merges.

**Option B — a post-merge / merge-queue suite run (strongest).**
Adopt a merge queue (or a required status check that runs the full suite on the
*prospective merge commit*), so the suite runs on the exact post-merge tree and
a red composition never lands. More infrastructure; best guarantee.

**Option C — a nightly / on-`main`-push suite run (detect, don't prevent).**
A scheduled or push-triggered full-suite run on `main` that alerts on red.
Detects the composition failure fast but does not prevent it landing.

Recommended: **A now** (immediate, low cost), **B** if merge volume grows.

## Negative control

Whichever option is chosen ships a demonstration: a deliberately conflicting pair
of changes to one function (green individually) must be caught red by the gate
before landing on `main` (Option A/B) or flagged immediately after (Option C).

## Owner decision points

- Which option (A / B / C)?
- Acceptable to serialize merges (Option A/B) given current PR volume?
- Does the existing CI run the full `pytest` suite, or a subset? (The gate is
  only as good as the suite it runs — confirm coverage of the seam.)
