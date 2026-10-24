# Confirmation: WP9.1 stage B design note, revision 3, and the owner annex (`8a0d68fc`)

**Date:** 2026-10-24<br>
**Reviewer:** the session that wrote the review (`4bf94d61`) and the re-review (`71d01975`). It is distinct from the
author.<br>
**Subject:** revision 3 at `8a0d68fc`, diff `71d01975..8a0d68fc`, one commit:
- the note (`transition/w9/wp9-1-stage-b-design-note.md`);
- the annex (`transition/w9/wp9-1-catalogue-owner-annex.yaml`, blob `4e648b7f`, 61 rows);
- the reconciliation §4;
- P-073, and P-072's correction pointer.

**Known limit (P-058):** one model family.<br>
**Edits:** none to the subject.

## Verdict

**PASS WITH FINDINGS.** 0 Blocking, 1 Major, 3 Minor and 2 Info findings.

Every re-review finding is closed, and each closure can be traced to annex text. The Major (c-1) is a one-clause gap in
LR-016's stop rule. Its corrected text is given below, and it may be folded in without another round. Stephen
decides whether to do that.

## Closure of the re-review

| Finding | Closed by |
|---|---|
| M-1 same bytes | Every request row (for example LR-007) binds "the proposal's pre-assigned rev_ ID as the new review's ID". G5 now requires the record's refs to be exactly the pre-assigned IDs. LR-016 lists every ownership record, and LR-020 refuses if the set computed at commit differs. W9-C23 binds every record-writing resolution |
| M-2 G5 scope | G5 is scoped to Stephen-resolved rows that write a W9 record, excluding the recovery, eligibility and pilot Decisions. LR-037 states "G5 does not apply … never the recovery root" |
| M-3 facts with no producer | LR-024 and LR-025: Stephen resolves the eligibility Decision before the review, with §11.2 a–c bound. LR-026 requires the named session, and LR-027 requires the metadata to match. LR-021 and LR-022: the pilot outcome Decision (`result_interpretation`) is read by LR-016, LR-035 and LR-054. LR-003 reads D-5's control-output files at `git_head` |
| M-4 shape tests only | `catalogue_tests` W9-C20 to W9-C25. Every row without a W9-T test binds at least one W9-C2x (checked below) |
| m-1 to m-7 | Named reviewer on every record-review row; `suspension_rule` defines "source" and "relies on"; LR-060 targets `P:legacy-adoption-status`; one ownership event token, and structured `{event, multiplicity, condition}` entries; T5 and W9-C24 on LR-050; `derivation_rules` (24 fields, content-hash rule, row hash including `source_refs`, the proposal's `created_at`); P-072's correction pointer; fixtures on LR-044 and LR-054, and S-007 on the post-review decision proposals |

**Mechanical checks** (read-only script, `python -I`):
- 61 rows, one key set of 20 keys;
- IDs LR-001 to LR-061, contiguous;
- `logical_key == payload_discriminant`, and `receipt_identity == "R:" + logical_key`, on every row;
- every test is in W9-T1 to W9-T23 or W9-C20 to W9-C25;
- every fixture is in F-001 to F-038 or S-001 to S-017;
- every row without a W9-T test has a reason and at least one W9-C2x test, and no row has both a W9-T test and a
  reason;
- every event entry is `{event, multiplicity ∈ {1, 0..n}, condition}` with a token matching `(E|W2):[A-Za-z0-9-]+`;
- the ownership record kind uses one `-recorded` token;
- every `record_schema_id` is a stage A schema except the two B1 adds.

Note §5's test map matches the annex.

## Residuals

- **c-1 (Major). LR-016's stop rule passes when no outcome exists yet.** LR-016 requires "no integration-pilot
  outcome Decision records a missed threshold". Before the pilot's outcome Decision (LR-022) exists, that condition
  holds vacuously. So a second batch can be proposed, reviewed and accepted after the pilot batch and before the
  pilot is judged. W9 §14.2 makes the *first* batch the pilot, and §14.3 says a missed threshold stops further
  batches. Both assume the outcome is known before a second batch.

  **Fix text:** "a batch after the first requires the integration-pilot outcome Decision resolved as passed; the
  first batch is the integration pilot: closed-reference items only, at most 20 (W9 §14.2, §14.3; 06v L-4)."
  This is the positive form that LR-035 and LR-054 already use.
- **c-2 (Minor). LR-055's fixtures were dropped without a record.** In revision 2 (LR-051) this row listed F-006,
  F-019, F-037 and F-038. In revision 3 (LR-055) the list is empty, and the reconciliation §4 does not mention it.
  W9 §12.3 assigns F-006 to "Paper-root transitions", and `successor_owned → closed_reference` of a root is one.
  Restore the four fixtures, or record why the row is exempt.
- **c-3 (Minor). The ownership record kind still has two projection and reducer names.**
  - LR-020 writes ownership records under `P:legacy-ownership` with reducer `U:legacy-closed-reference-acceptance`.
  - LR-054 and LR-055 write them under `P:legacy-ownership-transitioned` with `U:legacy-ownership-transitioned`.

  This is the projection-level form of the re-review's m-3. Name one projection and reducer for the ownership kind in
  all three rows.
- **c-4 (Minor). No annex generator is committed.**
  - Reconciliation §4 (M-4) says "the annex generator checks the rule". No such tool is in the tree; the only search
    hit is the annex itself.
  - The rule is stated in `derivation_rules`. The B1 verifier (`tools/verify_w9_materialization.py`) should check it,
    with a negative control: a row with no W9-T test and no W9-C2x test must fail.
  - Change the reconciliation's wording so that it does not claim an uncommitted check.
- **i-1 (Info).** LR-035 and LR-054 cite "LR integration_pilot_outcome" by discriminant rather than by row ID
  (LR-022). That is harmless, but LR-022 would be exact.
- **i-2 (Info).** One model family (P-058 known limit).

## Commands run (read-only)

```text
git checkout pipe/w9-wp9-1-catalogue                          # HEAD 8a0d68fc
git log --oneline 71d01975..HEAD; git diff --stat 71d01975..HEAD
git diff 71d01975..HEAD -- 03-decisions-and-open-questions.md reviews/ transition/w9/wp9-1-stage-b-design-note.md
git ls-tree HEAD <annex>; sed -n 1,80p <annex>
git show 479745fc:<annex> > <scratchpad>/rr/annex-r2.yaml     # revision 2 comparison for c-2, c-3
/c/Users/steph/TDL/.venv/Scripts/python.exe -I <scratchpad>/rr/probe3.py <repo>
/c/Users/steph/TDL/.venv/Scripts/python.exe -I <scratchpad>/rr/rows3.py <repo> <17 row ids>
grep -rn 'annex generator|owner_annex' --include=*.py .         # no generator committed
```
