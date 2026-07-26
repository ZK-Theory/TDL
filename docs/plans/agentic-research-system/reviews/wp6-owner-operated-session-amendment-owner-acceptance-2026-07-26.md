# WP6 owner-operated-session amendment acceptance

**Date:** 2026-07-26  
**Decision:** `accepted_for_governing_planning`  
**Owner:** Stephen Dorman  
**Authority:** P-042 and Stephen's merge of PR #165 followed by the explicit
instruction to close the amendment acceptance gate  
**Runtime authority:** none

## Exact accepted subject

| Identity | Value |
|---|---|
| Pull request | `https://github.com/stephendor/TDL/pull/165` |
| Reviewed/remediated head | `b736582d7ab4a3ae9d53c5e3d853e21ad1b180dc` |
| Merge commit | `f19727641ae74f3f60982d384cdee59c15976404` |
| Shared tree | `9f94eb81de182c564714af6cb7b15298ff13f919` |
| 06g blob | `49696e5b737f59ab8bd58d18c6e9231b0a61a599` |
| implementation index blob | `c8a8d977d6bd888351b60cdaf56e3d58e1a86388` |
| root index blob | `f655166e8422fffc314a1b27c52c447b53a0a9bd` |

The PR head and merge commit resolve to the same tree. The embedded
`owner_direction_accepted_review_pending` field in 06g is candidate-snapshot
state; this external record supplies its effective post-review status without
rewriting the reviewed artifact.

## Review and remediation evidence

CodeRabbit reviewed initial head
`eee3fce9447e403ecb2d34c09a1e8f57e77b5f75` and returned two actionable Major
findings:

1. bind operator, session/handoff, reviewer, and independent-context provenance
   in the evidence contract;
2. keep the revised WP6 path non-dispatchable until review and acceptance.

Both findings were verified as valid and remediated in
`b736582d7ab4a3ae9d53c5e3d853e21ad1b180dc`. Focused validation passed:
`git diff --check`, local Markdown-link resolution, and the repository hooks
applicable to the three changed documentation files. Stephen then merged the
exact remediated tree as PR #165.

## Effective disposition

The 06g amendment is accepted as the governing planning authority for the
owner-operated-session model:

- ARS does not invoke Claude or Codex or handle OAuth credentials;
- direct-provider WP6.2 activation remains deferred historical scope;
- the first-release dependency path is WP6.1 plus WP6.3 into WP6.4 and then
  Gate 6;
- KAN-56 may now perform the separate WP6.3 Gate A/readiness assessment.

This acceptance closes the 06g consistency-review prerequisite only. It does
not itself authorize WP6.3 implementation, WP6.4 dispatch, provider invocation,
credential access, Gate 6 acceptance, a pilot, an eligibility transition, a
result, or a claim.

