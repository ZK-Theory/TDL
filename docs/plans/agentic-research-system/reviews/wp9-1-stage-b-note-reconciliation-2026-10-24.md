# WP9.1 stage B design note reconciliation: revision 2 against the review of `0cf8acd3`

**Date:** 2026-10-24<br>
**Author:** the WP9.1 author session<br>
**Review:** `reviews/wp9-1-stage-b-note-review-0cf8acd3-2026-10-24.md` (commit `4bf94d61`). Verdict rework required:
2 Blocking, 6 Major, 7 Minor, 5 Info.<br>
**Owner decisions:** P-072. Stephen chose the recommended option on all seven owner points: B-1, B-2, M-1, M-4, M-5,
M-6 and m-7.<br>
**Status:** Revision 3 (§4) is ready for the reviewer's narrow confirmation. It is not accepted.

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

## 4. Revision 3, against the re-review of `479745fc`

The re-review (`reviews/wp9-1-stage-b-note-re-review-479745fc-2026-10-24.md`, commit `71d01975`) returned rework
required, narrow: 0 Blocking, 4 Major, 7 Minor and 6 Info findings. Stephen answered its four owner points (P-073).
The reviewer offered a narrow confirmation of the corrected annex.

| Finding | Disposition | Where |
|---|---|---|
| **M-1** same bytes | Fixed. Every review request binds the proposal's pre-assigned `rev_` as the new review's ID. G5 requires the record's refs to be exactly the pre-assigned IDs. W9-C23 refuses differing refs or bytes. LR-016's proposal lists every ownership record, and LR-020 refuses a different set at commit | Annex G5, request rows, LR-016, LR-020; note §2 |
| **M-2** G5 scope | Fixed. G5 is scoped to Stephen-resolved rows that write a W9 record. The recovery, reviewer-eligibility and integration-pilot Decisions are excluded, and LR-037 says so itself | Annex G5, LR-037 |
| **M-3** facts no row produces | Fixed by P-073 item 3. The eligibility Decision (LR-024, LR-025) is named by LR-026 and matched by LR-027. The integration-pilot outcome Decision (LR-021, LR-022) is read by LR-016, LR-035 and LR-054. LR-003 reads D-5's control-output hash files | Annex; note §4 |
| **M-4** shape tests only | Fixed by P-073 item 1: W9-C20 to W9-C25. Every authority-flow row binds at least one. The rule is stated in the annex's `derivation_rules`, and the B1 verifier enforces it with a negative control (confirmation c-4; the annex was authored with an uncommitted helper, which is not a control) | Annex `catalogue_tests`; note §3, §5 |
| **m-1** named reviewer | Fixed in every record-review row's subject and preconditions | Annex |
| **m-2** suspension inputs | Fixed. LR-060 projects `P:legacy-adoption-status`. `suspension_rule` defines "source" and "relies on" | Annex |
| **m-3** event tokens | Fixed. One token, `E:legacy-ownership-transitioned-recorded`, for every ownership record; `ordered_events` entries are `{event, multiplicity, condition}` | Annex; note §3 |
| **m-4** T5 placement | Fixed: T5 and W9-C24 are bound to LR-050 | Annex LR-050 |
| **m-5** derivation rules | Fixed. There are 24 fields. `derivation_rules` states the precondition scope, the content-hash rule, the row hash, the proposal's `created_at`, and that a changed applicability needs a new proposal | Annex; note §3 |
| **m-6** P-072 names | Fixed: P-072 carries a correction pointer (P-073 item 2) | Register |
| **m-7** fixtures | Fixed. LR-044 gets F-018, F-023 and F-037; LR-054 gets F-023; the decision-proposal rows after a review get S-007 | Annex |
| I-1, I-2, I-5, I-6 | Recorded. I-2 is carried in note §6 | Note §6 |
| **I-3** partition ordering | Carried to WP9.2 in note §6 | Note §6 |
| **I-4** O-31 reading | Recorded as Stephen's reading (P-073 item 4) | P-073; note §4 |

The annex now has 61 rows. The eligibility pair and the pilot-outcome pair are new, and the row numbers changed from
revision 2.

## 5. The confirmation's residuals

The confirmation (`reviews/wp9-1-stage-b-note-confirmation-8a0d68fc-2026-10-24.md`, commit `ba5ec32d`) returned PASS
WITH FINDINGS: 0 Blocking, 1 Major, 3 Minor and 2 Info findings. Stephen asked for all of them to be folded in with no
further round.

| Finding | Disposition |
|---|---|
| **c-1** LR-016's stop rule passed vacuously before the pilot outcome existed | Fixed with the reviewer's exact text: "a batch after the first requires the integration-pilot outcome Decision resolved as passed; the first batch is the integration pilot: closed-reference items only, at most 20 (W9 §14.2, §14.3; 06v L-4)" |
| **c-2** LR-055's fixtures dropped | Restored: F-006, F-019, F-037, and F-038 when the root's families use the TDA pack's lanes |
| **c-3** two ownership projection and reducer names | Fixed. LR-020 writes ownership records under `P:legacy-ownership-transitioned` with `U:legacy-ownership-transitioned`, as LR-054 and LR-055 do |
| **c-4** the uncommitted generator claim | §4's M-4 wording is corrected. The B1 verifier enforces the rule, with a negative control |
| **i-1** cite by row | LR-035 and LR-054 now cite "LR-022" |
| i-2 | Recorded |

## 6. Not done

Nothing is materialized: no schema change, no catalogue, no verifier. Nothing is pushed.
