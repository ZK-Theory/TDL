# WP6.7 legacy-consolidation sequencing exact-subject review

- Review date: 2026-08-01
- Independent review task: `/root/review_wp67_exact_subject`
- Reviewed branch: `codex/wp67-legacy-consolidation-sequencing`
- Reviewed subject: `edcb12979cbdf424c4a8bf96b5e8982c07f4fc27`
- Parent/base: `a464eb5aefed2645da48e4495efa61a27f0e3954`
- Reviewed path: `docs/plans/agentic-research-system/implementation/06l-wp6-7-legacy-consolidation-sequencing.md`
- Verdict: `rework_required`

## Exact-subject verification

The reviewer verified that the subject adds exactly the one reviewed path and
that `git diff --check` passes. The unrelated worktree-local changes to
`.claude/CLAUDE.md` and `.repowise-workspace.yaml` were excluded from the
review; evidence was read from exact Git objects.

The following cited evidence was independently re-resolved:

- PR #72 merge `703101de` is an ancestor of the reviewed subject;
- the cited T1.28 result blobs and byte counts match (`b1a9dd...`, 10,485
  bytes; `a09de1...`, 9,444 bytes);
- the result JSON records USoc 12/12 and BHPS 9/11 W2 rejections;
- all eight repository citations resolve at the exact subject; and
- live read-only Jira state matches the document: KAN-22 is In Progress;
  KAN-23 through KAN-26, KAN-21, KAN-60, and KAN-61 are To Do; KAN-12 is In
  Progress. KAN-22 and KAN-21 block KAN-60, and KAN-60 and KAN-61 block
  KAN-12.

The review also confirmed that W0, A-001, A-002, Stage 2, Gate 6, W9, W11,
and ownership-transition prerequisites remain open. The subject does not
close KAN-22 or authorize migration, cutover, deprecation, or retirement.

## Findings

### M-01 — Gate 7 ordering contradicts the owner-approved W9 brief

Lines 167–227 of the reviewed `06l` subject make the post-terminal W0 addendum
and A-001/A-002 Stage-2 disposition prerequisites for W9/Gate-7 acceptance and
opening. This conflicts with
`docs/plans/agentic-research-system/handoffs/07-w9-gate7-legacy-integration-authoring-brief.md`
lines 17–36, 44–53, and 99–104. That owner-approved route commissions W9 and
Gate-7 authoring now and defines the W0 addendum plus bounded delta review as
Gate 7's first intake deliverable, not a blocker on opening it. Dispatch still
requires Gate-6 pilot-promotion evidence and a separate Stephen decision.

Required correction:

- separate W9/Gate-7 authoring, review, and acceptance from the later Gate-7
  opening decision;
- retain the W0 addendum and bounded delta review as first Gate-7 intake work;
- retain A-001/A-002 and full Stage-2 disposition as legacy-closeout
  conditions for affected ownership transition, cutover, deprecation, or
  retirement; and
- do not create a new opening precondition without an explicit owner
  amendment.

### m-01 — Missing navigation registration

The implementation README lists the WP6 suite but has no inbound reference to
the new `06l` record. The existing
`06i-wp6-1-artefact-authority-and-consumer-firewall-plan.md` is a distinct path
and scope, not a collision. Add a neutral navigation link to the corrected
`06l` record.

## Disposition boundary

One minimal author-remediation cycle is required, followed by a fresh
independent exact-subject review. This record is not owner acceptance and does
not authorize Gate-7 opening, ownership transition, migration, cutover,
deprecation, retirement, provider activity, dispatch, or KAN-22 closure.
