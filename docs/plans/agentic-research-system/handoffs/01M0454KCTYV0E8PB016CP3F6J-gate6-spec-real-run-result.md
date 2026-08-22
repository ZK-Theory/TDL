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
the historical run at position 444, `ResourcesReleased`. Later store events
exist. This is real-run proof of the historical route, not proof of integrated
code.

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

## Durable evidence anchors

The operational source of truth is the immutable control store selected by
locator `wp64-gate6-historical-control`. The repository-tracked
[machine-readable retrieval manifest](01M0454KCTYV0E8PB016CP3F6J-gate6-spec-real-run-evidence-manifest.json)
binds the locator and approved-binding hash to the store identity manifest,
historical Task object, exact ledger files, registered artefact-object records,
content paths, sizes, and independently recomputed file hashes. An authorised
reviewer resolves the locator through the approved project binding or a
byte-exact verified restore, verifies the expected store/project identities,
and can then retrieve and hash every named relative path. The internal
artefact bytes and host path are not repeated in this public handoff. The final
governed same-disk export and fresh-root restore remain an explicit Gate 6
closure step in 06q; off-disk machine-loss resilience is a separate deferred
job. The store was read without writing it:

- project identity: `prj_01978abc-1000-7000-8000-000000001000`;
- store identity:
  `2df87684ef33136d85adff91d58a8e91fc31a061a53ced6932988df4e687cd7a`;
- manifest hash:
  `80c2e7d3e11aeeb5ddc6723243895374531afadc5770b5fb73b566764f3dfcb2`;
- position 432, `DecisionResolved`, event hash
  `aab242f6cb0cf797d2a6b0b6e976f3495ed8962fba8539f09458ddd98e5870bb`,
  selects `PARK` for decision
  `dec_0f30520f-f622-7c2f-80ba-53b91ecd5b63`;
- position 433, `CandidatePromotionApplied`, event hash
  `02162f0a0608feb1893260e219e43a3036898ef0da19e27ee12630ea314ffeb2`,
  records the candidate as parked; and
- position 444, `ResourcesReleased`, event hash
  `ff738e0e548eb556faf520e72cce56c8acb1599ffab6a584ecea5ea6deb349da`,
  is the historical run-closure anchor. The store contains later events, so
  position 444 is not the current store tail.

The seven registered run artefacts were re-read from their anchored content
paths and all seven file bytes matched their registered SHA-256 values:

| Evidence | Artefact identity | Verified SHA-256 |
|---|---|---|
| Raw result | `art_449b7235-3114-7043-8b3e-6ca76dc14768` | `dc3811bd50423ebf7748e14d998e5cbe237e59b83661ee5feca0e78807139103` |
| Source | `art_2e7531f9-020b-7775-83c4-cac52a2f6fed` | `ac0d2c49c0563926a1a52aba91fe0dbd95d8d4e7c2d3143a6c3e4c23bcbc8464` |
| Checks | `art_f0cbbf39-1356-772a-86c2-fca6391bfa45` | `5705c5be0e9217c84dc8cefe9a7699913ca593dcc92fe1937c6bc650d3ef36be` |
| Summary | `art_ddf81b12-ffb4-7944-872f-aff3177b46c4` | `792eeccfba777963fd67bc7178ebdd0c3c751035b224473b9e05288ccb7358a8` |
| Return | `art_8e65db46-dd82-702b-84ff-c7282bc88c61` | `a334a81c61e803c5dad90078cc8be808230ec12b1c05c9272c39ccafaa7df14c` |
| Source correction | `art_f14d8ecc-9204-7ee3-a7be-6d72c870f986` | `01de9ae097a589deec560c0b1eef8739f4828cc96e4ecddc6f4f94ab6360c3c4` |
| Approval | `art_0b3578b7-c96f-7e0e-a6d0-a1a38ba9c1de` | `99407a4c96a5c5a00135fb02e7a04dac6034fe8750b2cc89d9aa8e804c62a024` |

The raw result and canonical return contain the exact 126-configuration and
42-rerun counts. The owner-decision events above establish the terminal `PARK`
disposition; the correction artefact preserves the source correction
append-only. The governance documents point to these anchors rather than
serving as evidence for one another.

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
   design, separate producer/reviewer/operator, and separate SPEC-02 approval.
   A SPEC-01 `PARK` must use the governed `OR-009`–`OR-011` Assay
   revisit/retry path and obtain a later exact `PROMOTE` before SPEC-02; the
   approval alone cannot bypass W11;
4. persist exact receipt/tail/identity/artefact/task/result bytes, close the
   terminal Task through `SubmitForReview` then `AcceptTask`, persist the fresh
   `ProjectUseDecision` through its public registration action and separate
   independent review/use-authority action, run historical and fresh read-only result commands,
   and verify governed backup/restore using the approved
   `wp64-gate6-backup-root` and `wp64-gate6-restore-verification-root`
   locators;
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
P-050 records the `PARK` outcome. Same-disk backup verification proves Gate 6
logical recovery only; encrypted off-disk replication and hash readback remain
a separate machine-loss-resilience capability rather than a Gate 6 closure
requirement. Gate 7 remains blocked on
integrated Gate 6 and final closure evidence. No scientific promotion is
implied.
