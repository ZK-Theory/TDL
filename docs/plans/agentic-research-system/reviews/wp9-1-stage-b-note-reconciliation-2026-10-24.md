# WP9.1 stage B design note reconciliation: revision 2 against the review of `0cf8acd3`

**Date:** 2026-10-24<br>
**Author:** the WP9.1 author session<br>
**Review:** `reviews/wp9-1-stage-b-note-review-0cf8acd3-2026-10-24.md` (commit `4bf94d61`). Verdict rework required:
2 Blocking, 6 Major, 7 Minor, 5 Info.<br>
**Owner decisions:** P-072. Stephen chose the recommended option on all seven owner points: B-1, B-2, M-1, M-4, M-5,
M-6 and m-7.<br>
**Status:** Revision 2 is ready for re-review. It is not accepted.

## 1. Files

| File | Change |
|---|---|
| `transition/w9/wp9-1-stage-b-design-note.md` | Revision 2: rewritten around the authority flow and the owner annex |
| `transition/w9/wp9-1-catalogue-owner-annex.yaml` | New: the normative owner annex, with G1 to G5 and 57 rows |
| `03-decisions-and-open-questions.md` | P-072, and an amendment pointer on P-071 |
| this file | New |

## 2. Dispositions

| Finding | Disposition | Where |
|---|---|---|
| **B-1** no review or decision route | Fixed by P-072 item 1. W9-path rows follow W11's pattern, verified at `service.py:3713-3720` and `discovery/commands.py:14-44`. The five-step authority flow uses pre-assigned IDs, and the record is written only at resolution. The resolver is named `ResolveW9AuthorityDecision` to keep the command-type sets disjoint (note §7, open point 2) | Note §1, §2; annex |
| **B-2** registration-grained ownership | Fixed by P-072 item 2 (the reviewer's text). LR-020 emits ownership events only for whole-file observations. LR-046 to LR-051 refuse `legacy_owned → closed_reference` | Note §4; annex LR-020, LR-046 to LR-051 |
| **M-1** suspension triggers and payload | Fixed by P-072 item 3. Suspension is a projection covering any re-observation (gap 1), supersession and a recorded use-time mismatch. LR-057 `RecordAdoptionUseMismatch` has its own 14th record kind (gaps 2 and 3). No suspension event | Note §4; annex LR-015, LR-056, LR-057 |
| **M-2** no independent expected side | Fixed. The annex is normative and machine-readable. The verifier derives expected rows from its blob, and `owner_annex_ref` replaces `file_observation_ref`. Stephen's O-8 acceptance names the annex (P-072 item 6) | Note §3 |
| **M-3** missing preconditions | Fixed: every precondition in the review's table is in its row, with its source, and the "/ S" rows carry G5 | Annex; note §4 |
| **M-4** fixtures and adoption coverage | Fixed by P-072 item 4. `pilot_promotion_fixtures` is on every record-emitting row, with W9 §12.3 conditions. LR-021 requires the §11.2 coverage record, checked by Stephen before the review starts | Annex; note §4 |
| **M-5** no revision route | Fixed by P-072 item 5: LR-002 `ImportAcceptedW9CatalogueRevision`, inert in v1 | Annex LR-002 |
| **M-6** stage B identities | Fixed by P-072 item 6. B1 widens the schemas and adds the verifier; B2 adds the catalogue pinned at B1's main commit. The envelope instance is written at L-3 or with `accepted_w9.py` | Note §6 |
| **m-1** binding tests | Fixed: T10 removed from registration; T6 added to LR-025, LR-040 and LR-050; T9 added to LR-056; T1 added to LR-025; T18 and T23 stated as tool-level and unit-level in v1 | Note §5 |
| **m-2** W9-C rule and literals | Fixed. The literals are `W9-C01-LR-nnn`, `W9-C03-LR-nnn-owner-row-mutation` and `W9-C11-LR-nnn`. An empty `binding_tests` needs one of two closed `w9c_only_reason` values. Extending SB-Q6 to authority-flow steps is put to Stephen (note §7, open point 1) | Note §3, §7 |
| **m-3** exact row shape | Fixed: 23 fields with required and nullable stated; `eligible_actor` is the submitter; per-record streams; `x0..n` notation; the `anyRef` kinds deferred by name | Note §3, §7 |
| **m-4** variant rows | Fixed: the paper roots split (ordinary, recovery); the ownership resolutions split | Annex LR-031 to LR-034, LR-050, LR-051 |
| **m-5** naming | Fixed: content is proposed by `ProposeLegacyRecord` and committed at resolution | Note §2, §4 |
| **m-6** LR-008 and LR-009 preconditions | Fixed: discharge `item_id` resolution and an accepted result; recovery predecessor `successor_owned`; ordinary root after the integration pilot | Annex LR-026, LR-031, LR-032 to LR-034 |
| **m-7** verifier paths | Fixed by P-072 item 7 | P-072; note §3, §6 |
| I-1, I-2, I-3, I-5 | Recorded | — |
| **I-4** O-31 reading | Stated as an open point | Note §7, open point 4 |

## 3. Points for the re-reviewer to test

1. **The authority flow:**
   - Proposal content carries pre-assigned IDs.
   - Resolution emits the record in the same transaction.
   - No path writes a record whose bytes differ from the reviewed proposal.
2. **The 57 rows' authority subjects.** Each must be exact under G4.
3. **The annex as a verifier input.** Is it parseable and complete, so that every derived field follows mechanically?
4. **Open points 1 to 4** in note §7.

## 4. Not done

Nothing is materialized: no schema change, no catalogue, no verifier. Nothing is pushed.
