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

**Option B — a merge-queue / prospective-merge-commit suite run (strongest).**
Adopt a merge queue (or a required status check that runs the full suite on the
*prospective merge commit*, before it lands), so the suite runs on the exact
tree that merging *would* produce and a red composition never lands. This is
strictly pre-merge validation — the check runs on a candidate commit and gates
the merge; it does **not** run after the merge. (True post-merge execution is
Option C: it can only *detect* a bad composition after it has already landed, so
it cannot support the "never lands" guarantee and must not be folded into B.)
More infrastructure; best guarantee.

**Option C — a nightly / on-`main`-push (post-merge) suite run (detect, don't prevent).**
A scheduled or push-triggered full-suite run on `main` *after* commits land, that
alerts on red. This is the only option that runs post-merge; it detects the
composition failure fast but by construction does not prevent it landing.

Recommended: **A now** (immediate, low cost), **B** if merge volume grows.

## Negative control

Whichever option is chosen ships a demonstration to the repo's established
gate-liveness acceptance criteria — a documented claim of "the gate works" is not
evidence; a watched failure is. The demonstration must record:

1. **Linked-worktree execution** — construct the deliberately conflicting pair of
   changes to one function (each green in isolation) in linked worktrees, not
   inline on `main`.
2. **Observed non-zero failure with the verbatim diagnostic** — run the gate
   against the composed tree and capture the actual non-zero exit and the exact
   test-failure output it emitted (not a paraphrase).
3. **Restoration confirmation** — revert/resolve the conflict and confirm the
   tree is back to a known-good state.
4. **Clean-tree pass** — re-run the gate on the restored tree and capture the
   green result, proving the gate is decisive in both directions (fires on red,
   passes on green) rather than always-failing.
5. **Evidence-register output** — emit the run into the gate-liveness evidence
   register so the "has anyone watched this fail?" question has a durable answer.

For Option A/B the failure must be caught **before** landing on `main`; for
Option C it is flagged immediately **after** landing (matching C's detect-only
role).

## Owner decision points

- Which option (A / B / C)?
- Acceptable to serialize merges (Option A/B) given current PR volume?
- Does the existing CI run the full `pytest` suite, or a subset? (The gate is
  only as good as the suite it runs — confirm coverage of the seam.)
