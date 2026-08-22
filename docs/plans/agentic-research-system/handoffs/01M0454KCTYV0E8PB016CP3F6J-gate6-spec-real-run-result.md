# Gate 6 SPEC real-run result and reset handoff

**Recorded:** 2026-08-22
**Status:** `PROVEN historical result / implementation not integrated`
**Current base:** `d64c58fa4366e5d7a0b7ddc5b2e0519edafcffd7`
**Active plan:** [06q — Gate 6 Recovery and Closure Plan](../implementation/06q-gate6-spec-real-run-integration-and-follow-up.md)

## Plain-English result

Yes, a real Gate 6 research workflow was run and it produced durable evidence.
No, Gate 6 is not closed: the implementation that produced the result has not
been integrated on `main`.

The historical run assessed a real paper and repository through SPEC-01, then
ran SPEC-02 as a bounded methods spike. It executed 126 frozen configurations
and 42 deterministic reruns, reached `PROVEN/spec_02_owner_decided`, and closed
the ledger at event 444, `ResourcesReleased`. This is real-run proof of the
historical route, not proof of integrated code.

## Research disposition

The result is **PARK**. Retain the spectral persistent-homology method as an
experimental or benchmark candidate. Do not use it as the default empirical
method or as the basis of a scientific claim. The run used synthetic data and
did not estimate a substantive effect. Upstream `vis_utils` equivalence and
the project's estimand/representation freeze remain separate empirical-
adoption work.

The `neurips2024` source is a valid lightweight Git tag at commit
`145efcde673f1a1897eff250b77221d26c34c479`. The initial source error was
corrected append-only. The correction does not promote the method or open Gate
7.

## Current Git and review state

- PR #257 remains an open draft candidate at `dea803490...`; it is obsolete and
  must be closed unmerged only after a replacement decision is durable.
- PR #258 is closed unmerged at
  `94f8bc1fc92bdc5259acab02e73a3958202ab2e`; its branch remains historical.
  It had 145 changed files, 35,796 additions, 114 review threads, and seven
  unresolved P1 families.
- The seven unresolved PR #258 P1 families are: legacy corrections not bound
  to their causal prefix; binding advance unanchored to `WriterLock`;
  brief-input actions completing without sealed identity; public commands
  bypassing the repaired-binding loader; owner context including unsealed
  SPEC-02 approvals; registered-content recovery enumerating an unanchored
  directory; and grants outliving the actor session.
- Separately, SF1-SF6 are action-model controls: total action state, exact
  completion tuple, retry ordering/authority expiry, one status/admission
  interpretation, unrelated isolation, and historical compatibility. The two
  lists are not interchangeable.
- No live store write is part of construction. A single binding is permitted
  only after all six replacement slices merge and the owner authorizes the
  closure sequence.

## Next bounded action

Follow [06q](../implementation/06q-gate6-spec-real-run-integration-and-follow-up.md):

1. complete the documentation-only reset (Step 0);
2. implement and independently test the six sequential latest-`main` PRs:
   `G6-SPEC-SOURCE-1`, `G6-SPEC-STORE-1`, `G6-SPEC-AUTHORITY-1`,
   `G6-SPEC-TASK-1`, `G6-SPEC-MODEL-1`, and `G6-SPEC-EXEC-1`;
3. after all six merge, perform final assembled selection and independent
   exact-`main` review, then admit one owner-reviewed successor binding; append
   `tsk_60c5549e-d11f-7d17-8145-d80e144aa537` acceptance and historical P-050
   `ProjectUseDecision`; obtain explicit paid-run approval; repeat
   Damrich/Berens/Kobak on real `neurips2024` with new IDs and frozen 126/42
   design, separate producer/reviewer/operator, and separate SPEC-02 approval;
4. persist exact receipt/tail/identity/artefact/task/result bytes, close the
   terminal Task through `SubmitForReview` then `AcceptTask`, persist the fresh
   `ProjectUseDecision`, run historical and fresh read-only result commands,
   and verify governed backup/restore at
   `C:\Users\steph\TDL-ARS-WP64-Backups` and
   `C:\Users\steph\TDL-ARS-WP64-Restore-Verification`;
5. obtain independent final evidence review, Stephen's closure, a docs-only
   final PR, merged-main replay, and `agent_docs`/Jira/docs reconciliation with
   KAN-103/KAN-12 transitions. No automatic paid rerun follows a production
   defect.

Terra XHigh owns implementation, the independent tester owns direct negative
proof, and Sol Medium reviews the whole store/model/execution boundary.
Stephen alone triggers CodeRabbit and authorizes merge. No plan text authorizes
those review/merge actions, and none has occurred.

## Hard boundaries and residual risks

SCALE-01 v1.0.3 and its eligibility envelope are historical and not a Gate 6
closure prerequisite. P-049 retains the merge/integration/closure distinction;
P-050 records the `PARK` outcome. Same-disk backup verification proves logical
recovery only; off-disk copying is separate. Gate 7 remains blocked on
integrated Gate 6 and final closure evidence. No scientific promotion is
implied.
