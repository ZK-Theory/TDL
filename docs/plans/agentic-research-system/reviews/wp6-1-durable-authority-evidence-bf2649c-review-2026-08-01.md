# WP6.1 durable authority-evidence exact-subject review

Date: 2026-08-01 (Europe/London)

Verdict: `accept_exact_subject`

Findings: 0 Critical, 0 Major, 0 Minor.

This record preserves the independent review of one exact corrective subject. It is not owner acceptance, merge evidence, completion of the remaining WP6.1 catalogue, or Gate 6 closure.

## Independent review identity

- Reviewer task: `019fbda5-07a5-7d52-8e8f-5b1827400deb`
- Review worktree: `C:\Users\steph\.codex\worktrees\624f\TDL`
- Subject: `bf2649c6a6fbc02bbd66e1b16403f564e1a22029`
- Parent: `0454ce9614f8ebcfe48fc68c441833738ee0b3bd`
- Tree: `0d51126f7e9b417ff7d4be92f25619c4989cdcda`
- Exact corrective delta:
  - `research_system/command/service.py`
  - `tests/research_system/integration/test_wp6_1_scope_task_authority.py`
  - `tests/research_system/unit/test_release_publication.py`
- Required ancestry was present, including main merge `6c32f17a7951ee1a01ca48b9fcaf7782125ac09e`, PR 201 head `75d27ef8caca506b6a98e75f4f819355eeb964a0`, and the prior WP6.1 subjects.
- The local review ref resolved to the subject. The review worktree remained detached after its single permitted switch attempt; `HEAD` and status stayed exact and clean. No remote review ref was required or used.

The reviewer received fresh exact-subject context and was prohibited from remediation, commits, pushes, PR or Jira operations, provider use, live records, and owner action.

## Closure of the prior defect

The prior review found that a lifecycle event carried only a grant ID and that deleting the disposable scoped-authority index could allow retry/restart behavior without a canonical ledger-history and grant-hash join.

The reviewed correction closes that gap at the real service seam:

- `CommandService.submit` holds `runtime/writer.lock` across current authority resolution, receipt lookup or reconstruction, append, and receipt return.
- Every lifecycle submission resolves through the exact `LedgerAuthorityGrantResolver`, then compares the complete current resolution with replayed activation/revocation history and the event/receipt identity.
- The scoped index is cache-only and may be rebuilt only after canonical resolution succeeds.
- Legitimate index deletion rebuilds deterministically, appends no event, preserves the original receipt, and uses the current canonical grant hash.
- Duck/substitution resolvers remain rejected, and no production fixture resolver was added.

Independent disposable-store mutations covered missing, tampered, ambiguous or duplicate evidence; object and activation-history hash disagreement; actor, scope, schema, risk, or time changes; and revocation after acceptance. Each failed closed without a new domain event, receipt change, or unverified index reconstruction.

## Validation evidence

- Complete changed authority integration file: 14 passed.
- Targeted lifecycle create/amend/supersede and replay tier: 3 passed.
- Targeted authority retry/replay tier: 2 passed.
- Missing-index restart reconstruction: 1 passed.
- Accepted-receipt ledger reconciliation: 1 passed.
- Gate 5 restore/supersession/S-014/S-015 tier: 20 passed, 23 deselected.
- Exact changed release-publication negative: 1 passed.
- Ruff on all three changed paths: passed.
- `git diff --check`: passed.
- Final review status: clean.

A broader combined test selection exceeded the 60-second execution window. It was not counted as evidence and was not repeated; bounded named slices supplied the acceptance evidence above.

## Protected evidence

- 87 command schemas and 86 event schemas remained present; all 173 governed WP6.1 schema blobs matched the current-main merge.
- The three governed WP6.1 contract blobs matched exactly.
- The runtime registry remained at 28 bindings, including the six active lifecycle commands.
- No accepted event payload, schema, contract, registry, or active binding changed in the exact corrective delta.

## Scope boundary

This verdict accepts only the durable authority-evidence correction at `bf2649c6...`. It closes R0 authority for the six already active Scope/Task lifecycle rows. It does not activate or complete the remaining accepted WP6.1 lifecycle catalogue and does not by itself make KAN-65 Done.
