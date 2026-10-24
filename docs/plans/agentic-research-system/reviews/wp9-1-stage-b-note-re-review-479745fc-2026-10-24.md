# Re-review: WP9.1 stage B design note, revision 2, and the owner annex (`479745fc`)

**Date:** 2026-10-24<br>
**Reviewer:** the session that reviewed revision 1 (`reviews/wp9-1-stage-b-note-review-0cf8acd3-2026-10-24.md`,
`4bf94d61`). It is distinct from the author.<br>
**Subject**, at `479745fc` on `pipe/w9-wp9-1-catalogue` (diff `4bf94d61..479745fc`, one commit, four files):
- `transition/w9/wp9-1-stage-b-design-note.md`, revision 2 (blob `e05c4d69`);
- `transition/w9/wp9-1-catalogue-owner-annex.yaml` (blob `c000d129`), with G1 to G5 and 57 rows;
- `reviews/wp9-1-stage-b-note-reconciliation-2026-10-24.md`;
- P-072, and the amendment pointer on P-071.

**Known limit (P-058).** This chain runs on one model family. That is recorded as a known limit, not as a finding.<br>
**Edits:** none to the subject. This file is the only file written.

## 1. Verdict

**`rework_required`, narrow.** 0 Blocking, 4 Major, 7 Minor and 6 Info findings.

Every finding of the first review is closed or reduced to one of the residuals below (§6). The derivation rule is
right now. The five-step flow follows W11 (`discovery/commands.py:14-44`; OR-122 to OR-133), and the citation it rests
on checks out (`service.py:3713-3720`).

The annex parses, and every derived field follows mechanically, with the two exceptions in m-3 and m-5. The authority
subjects are exact except one family (m-1).

What remains are textual fixes to G5 and about a dozen rows, plus two owner confirmations (M-4; m-6). None needs a
further full round. A narrow confirmation of the corrected annex will do.

The four Majors:
- the pre-assigned IDs are bound at the decision step but not at the review step;
- LR-020's ownership records are written with bytes that no proposal holds;
- G5's stated scope would make the recovery Decision name its recovery root;
- several preconditions read facts that no row and no named record produces.

## 2. Major findings

### M-1 (Major). The same-bytes claim fails at two points

**Claim.** Note §2 (lines 51–52) says "The record is written only by step 5, so a reviewed proposal can never be
committed with different bytes", and that the pre-assigned IDs mean no hash depends on itself. The second half holds:
the proposal carries the `obj_`, `rev_` and `dec_` IDs as strings, the review and the Decision bind the proposal's
hash, and neither of their hashes enters the record. The first half fails at two points.

**Evidence and failure.**
1. **The review ID is not bound to the pre-assigned `rev_`.**
   - The decision-proposal rows bind "the pre-assigned `dec_` ID" in their authority subject (for example LR-004 and
     LR-024).
   - The review-request rows do not bind the review ID. LR-007 (annex line 192) and its siblings LR-012, LR-017,
     LR-022, LR-027, LR-037, LR-042, LR-047 and LR-053 have the subject "exact proposal subject + the named reviewer",
     with no requirement that the new review's ID equal the proposal's pre-assigned `rev_`.
   - G5 (annex line 7) checks "the review it names", meaning the review the Decision names. It never checks that the
     record's own `review_ref` (or `reviewer_ref`, `independent_review_ref`) is that review.

   *Failure:* the analyst requests review `rev_B` on the proposal. The proposal content, and so the record, cites
   pre-assigned `rev_A`, which is never created. `rev_B` comes back positive, the Decision names `rev_B`, and G5
   passes. The accepted record then cites a review that does not exist.
2. **LR-020 writes records no proposal holds.**
   - LR-020 (line 583) emits `E:legacy-ownership-transitioned x0..n`. These are full `legacy-ownership-transitioned`
     records: stage A requires `record_id`, `content_hash`, `subject_registration_ref`, `reviewer_ref` and
     `decision_ref`.
   - Their number is computed at resolution from the projection ("whose registration is legacy_owned").
   - LR-016's proposal (line 463) holds only the acceptance record, so none of these records' IDs or bytes is in the
     reviewed proposal or in the Decision's subject hash.

   *Failure:* between the review and the resolution, another batch moves one of the files. The resolution emits a
   different set of ownership records from the set the reviewer could have seen, and nobody reviewed or decided it.

**Impact.** Provenance and authority: the claim the reconciliation (§3 item 1) asked to be tested.

**Disposition.** Fix now.

**Proposed text.**
- In every `RequestW9AuthorityReview` row's authority subject: "exact proposal subject + the named reviewer + the
  proposal's pre-assigned `rev_` ID as the new review's ID".
- In G5: "…and the record's review and Decision refs are exactly the proposal's pre-assigned `rev_` and `dec_` IDs,
  which are the review satisfied and the Decision resolved."
- In LR-016: "the proposal lists, with pre-assigned IDs and full content, every `legacy-ownership-transitioned`
  record the resolution will emit; LR-020 refuses if the set computed at commit differs."

**Affected.** G5; nine review-request rows; LR-016, LR-020; WP9.2 preparers.

### M-2 (Major). G5's scope makes the recovery Decision name the recovery root

**Claim.** G5 says it binds "every row resolved by Stephen", and note §3 (lines 65–66) repeats that. Applied to
LR-033, it requires the recovery Decision's subject to be "this record's pre-assigned ID and exact content hash", that
is, the recovery root.

**Evidence.**
- W9 §13.1 says the recovery Decision "never names the recovery root".
- W9-T21's negative control is "a recovery Decision that names its recovery root … rejected".
- LR-033 (line 992) has resolver `stephen`. It states the correct rule ("naming only the predecessor root and the
  recovery intent"), but it does not say that G5 is excluded. The annex lists G5 inside the other resolve rows'
  preconditions and leaves it out of LR-033's, so the row text and the global's stated scope disagree.

**Failure.** A verifier, or a WP9.2 author, that applies the globals as written (note §3) builds LR-033 to require
what W9-T21 rejects. Under the restatement-diff rule, the narrower statement governs only when the exception is
stated. Here it is implicit.

**Disposition.** Fix now.

**Proposed text.** "G5 (every row resolved by Stephen that writes a W9 record; not LR-033, whose Decision names only
the predecessor root and the intent, W9 §13.1, W9-T21): …"

**Affected.** G5; LR-033; the verifier's precondition derivation (m-5).

### M-3 (Major). Preconditions that read facts no row produces

**Claim.** Several new preconditions depend on a fact for which neither a row nor a named record exists. The
preparer would have nothing to read. That is silent absence: the check is either skipped or always failed.

| Row | Precondition | What is missing |
|---|---|---|
| LR-021 (line 635) | "a §11.2 second-family coverage record … checked by Stephen before the review starts" | The record kind, its producer and where it lives. W9 §11.2(a) says the family is "recorded by the operator", and §11.2 says the check is made by "the item's independent reviewer, or Stephen". No row records Stephen's check. The reviewer is not yet named at LR-021, because LR-022 names the reviewer. Neither LR-022 nor LR-023 requires the named or recording reviewer to be the coverage record's session. W2's `RecordReviewVerdict` already carries `reviewer_model_metadata` and `reviewer_profile` (core schema), which could carry it |
| LR-016 | "after a missed threshold, no further batch" | No record of a batch's measured outcome against the §14.3 thresholds |
| LR-031, LR-050 | "the integration-pilot batch has passed" | The same: what record says "passed" |
| LR-003 (line 77) | "every §4.4 detector's negative control watched to fail" | Which committed evidence (06v D-5's filed output hashes, or a WP9.5 control record) the preparer reads |

**Failure.** WP9.2 implements LR-021 and finds no coverage record to read, so it either drops the check or invents a
record kind. Either way, P-072 item 4 is met only on paper.

**Disposition.** Fix now: name each record.

**Proposed text.**
- **LR-021, LR-022, LR-023.** The coverage record is a named kind, for example an operator-recorded W2 review
  requirement or an `art_` evidence file, or another kind Stephen names. Stephen's pre-review check is a resolved
  Decision before LR-022. LR-022 requires the named reviewer to be that record's session, and LR-023 requires the
  verdict's `reviewer_model_metadata` to match it.
- **The batch outcome.** It is a Stephen Decision (kind `result_interpretation`) citing the §14.3 pre-registration
  and the measured values. LR-016, LR-031 and LR-050 read it.
- **LR-003.** Cite the D-5 output-hash files in the W9 evidence area, read at the binding's `git_head`.

If the record kind for coverage is not settled, that choice is Stephen's.

**Affected.** LR-003, 016, 021 to 023, 031, 050; W9-D3; P-072 item 4; WP9.5, WP9.7.

### M-4 (Major). Open point 1: 39 rows would rely on shape tests only

**Claim.** The annex leaves `binding_tests` empty on 38 authority-flow rows and on LR-030 (39 of 57). Their only tests
would be the generic `W9-C01`, `W9-C03` and `W9-C11`. By note §3 and W11's precedent
(`test_w11_expected_catalogue.py:52-96`), those compare a catalogue row with its annex row. They prove the row was
transcribed. They do not prove that the command enforces anything.

**Evidence.** The controls that live only on those rows have no behavioural test anywhere:
- G3's independence rule;
- the session-distinct-from-the-analyst rule (W9 §8.6);
- the named-reviewer binding;
- the stale-hash refusal (S-007 is listed as a fixture, but no row-level test exercises it);
- the pre-assigned-ID binding (M-1);
- LR-046's refusal of `legacy_owned → closed_reference` (m-4).

**Disposition.** Owner decision. Extend P-071 item 6 only together with a behavioural test family.

**Proposed text.** Add to the annex a closed `W9-C2x` family, each test a negative control bound by the rows it
exercises:
- W9-C20: a reviewer who produced the item or shares the analyst's session; refused;
- W9-C21: a verdict from a reviewer other than the named one; refused;
- W9-C22: a request or verdict on a stale proposal hash; refused (S-007);
- W9-C23: a resolution whose record refs differ from the pre-assigned IDs, or whose bytes differ from the proposal;
  refused;
- W9-C24: a proposal for `legacy_owned → closed_reference`; refused.

`w9c_only_reason: authority_flow_step` then requires at least one `W9-C2x` in the row.

**Affected.** P-071 item 6; open point 1; the stage B verifier.

## 3. Minor findings

- **m-1. The record-review rows do not bind the named reviewer.** LR-008 (line 222) and its siblings have the subject
  "exact proposal subject (record ID + content hash)" and require only "the requested review open on the current
  hash". Add to their authority subject and preconditions: "the submitter is the reviewer the request named".
  Otherwise any actor of the class, holding a grant on the proposal, can record the verdict.
- **m-2. Suspension inputs.**
  - LR-056's `projection_targets` lacks `P:legacy-adoption-status`, although note §4 projects suspension from
    supersession. LR-015 and LR-057 list it.
  - "A record it relies on" is undefined. State the set: the adoption's observation, that observation's
    closed-reference acceptance, and the adoption itself.
  - "A later observation of its source" does not say whether "source" means the registration, or the registration
    plus the selector. For item-grained files the difference decides whether observing tracker row T1.7 suspends an
    adoption of row T1.3.
- **m-3. Event tokens.** LR-020 emits `E:legacy-ownership-transitioned`, and LR-050 and LR-051 emit
  `E:legacy-ownership-transitioned-recorded`, for the same record kind. A reducer or projection keyed on one name
  misses the other. LR-020's multiplicity is also prose inside the event string ("x0..n: one per accepted …"), which
  no token pattern for B1's widened `ordered_events` can hold. Use one event name, and add a structured multiplicity
  field.
- **m-4. W9-T5 is bound in the wrong place.** Note §5 binds T5 to LR-050 and LR-051 "including the refusal of
  `legacy_owned → closed_reference`". That refusal is a precondition of LR-046 (line 1366), whose `binding_tests` is
  empty. Bind T5 to LR-046 as well, or repeat the refusal in LR-050 and LR-051.
- **m-5. Derivation rules the verifier needs.**
  - The catalogue row has 24 fields, not 23. Note §3's table lists 24 names.
  - The catalogue's `preconditions` field: does it carry G1 to G5 expanded, or only the row's list? The resolve rows
    list G5 inline, and no row lists G1 to G4.
  - "Exact content hash" should name W11's rule: SHA-256 of `canonical_bytes` over the record without
    `content_hash` (`test_w11_expected_catalogue.py:126-128`).
  - `owner_annex_ref`'s row hash: is it canonical JSON of the YAML row with or without `source_refs`?
  - A resolution-written record's `created_at` and `created_by_actor_id` are the proposal's values. State this.
  - If Stephen changes per-item applicability in LR-020's Decision, a new proposal is needed.
- **m-6. P-072's text and revision 2 disagree.**
  - P-072 item 1 names "a W9 `ResolveDecision`". The note uses `ResolveW9AuthorityDecision` (open point 2).
  - P-072 item 2 names "LR-006's acceptance" and `TransitionLegacyOwnership`. Neither exists in revision 2: they are
    LR-020 and LR-046 to LR-051.

  The register should carry a correction pointer mapping the old names to the new rows, with Stephen's confirmation
  of the resolver's name.
- **m-7. Fixture gaps.**
  - LR-040 accepts the full path's observations but lists no fixtures. W9 §12.3 assigns F-018 and F-037 to "every
    result-family observation", and F-023 to "every import".
  - LR-050 lacks F-023.
  - The decision-proposal rows check "a positive review on the current hash" but do not list S-007.

## 4. Info

- **I-1. Mechanical checks on the annex,** by a read-only script with `python -I`:
  - 57 rows, all with the same 20 keys;
  - IDs LR-001 to LR-057, unique and contiguous;
  - `logical_key == payload_discriminant`, and `receipt_identity == "R:" + logical_key`, on every row;
  - every `binding_tests` entry is in W9-T1 to W9-T23;
  - every fixture is in F-001 to F-038 or S-001 to S-017;
  - an empty `binding_tests` always carries a reason, and a non-empty one never does;
  - every `record_schema_id` is a stage A schema except the two B1 adds (`legacy-adoption-use-mismatch`,
    `import-accepted-w9-catalogue-revision`).
- **I-2. Census size.** The annex has 12 distinct command types, so D-4's census grows by 12 runtime-binding rows at
  WP9.2, not 57.
- **I-3. Open point 2 is supported by the code.**
  - `ResolveDecision` is already in two command sets: generic W2 (`service.py:232`; `authority.py:313`) and Discovery
    (`commands.py:41`). Discovery tells them apart only by transaction ID (`DISCOVERY_RESOLVE_ROWS`,
    `commands.py:45-64`).
  - U-7's `legacy` predicate is keyed on command type, so a third `ResolveDecision` would need the same transaction
    bookkeeping. The distinct name is the simpler choice.
  - For WP9.2: W9 emits W2-typed events (`ReviewRequested`, `DecisionProposed`, `DecisionResolved`).
    `shared_event_partition` (`routes.py:301-319`) falls through to its event-type sets after the Discovery check, so
    the legacy predicate must come before those checks, or the W9 events land in `control`.
  - Stephen's confirmation is m-6.
- **I-4. Open point 3** (the `anyRef` kinds deferred by name to WP9.2) is acceptable. **Open point 4** (O-31's
  reading: the full-path rows are built and refuse until their gate) is a reasonable reading, but it is the author's.
  Record it as Stephen's, or as a register note, not only in the design note.
- **I-5. Annex identity.** The acceptance envelope (stage A) has no annex field. The annex is still bound
  transitively, because every catalogue row's `owner_annex_ref` carries the annex blob and SHA-256, and the envelope
  binds the catalogue. No change is needed.
- **I-6.** One model family (P-058 known limit).

## 5. Open points, dispositions

| Open point | Disposition |
|---|---|
| 1. Authority-flow rows with no §17 test | Owner decision: extend P-071 item 6 only with a behavioural `W9-C2x` family (M-4) |
| 2. `ResolveW9AuthorityDecision` | Keep. The code supports it (I-3). It needs Stephen to confirm, since P-072 item 1's text names `ResolveDecision` (m-6) |
| 3. `anyRef` kinds deferred to WP9.2 | Keep (I-4) |
| 4. O-31 reading | Keep the reading; record it in the register (I-4) |

## 6. Closure of the first review's findings

| Finding | Status | Evidence |
|---|---|---|
| B-1 review and decision route | Closed, subject to M-1 | Note §1–§2; annex rows for every reviewed or decided kind; citation verified |
| B-2 ownership grain | Closed, subject to m-3 and m-4 | LR-020 whole-file only; LR-046 refusal |
| M-1 suspension | Closed, subject to m-2 | Projection; any re-observation (LR-025 precondition); LR-057 with a 14th record; no event |
| M-2 expected side | Closed, subject to m-5 | The annex is normative; the verifier derives from its blob; `owner_annex_ref` |
| M-3 missing preconditions | Closed, subject to M-3 here | Every item of the first review's table is now in its row: LR-003, 015, 016, 035, 036, 050, 052, and G5 |
| M-4 fixtures and coverage | Fixtures closed, subject to m-7; coverage carried as M-3 here | |
| M-5 revision route | Closed | LR-002 |
| M-6 stage B identities | Closed | Note §6 |
| m-1 to m-7 | Closed | m-3's count error is carried in m-5 here |

## 7. Decision audit

| Decision | Disposition |
|---|---|
| P-072 item 1 (W9-path rows) | Keep; correct the resolver's name (m-6) |
| P-072 item 2 (item-grained ownership) | Keep; correct the row references (m-6); M-1 point 2 |
| P-072 item 3 (suspension as a projection) | Keep; m-2 |
| P-072 item 4 (fixtures; adoption coverage) | Keep; M-3 (the coverage record and the check need producers) |
| P-072 item 5 (revision import) | Keep |
| P-072 item 6 (B1 then B2; envelope at L-3 or in `accepted_w9.py`) | Keep |
| P-072 item 7 (verifier paths) | Keep |
| P-071 item 6 extension (open point 1) | Amend, as M-4 |
| P-069 item 2 (event payloads validated) | Keep. The proposal events validate against their record schemas (each Propose row's first precondition). WP9.2 must name the payload schema for the W2-typed events |
| P-070, P-066 item 2, D-2, D-3, D-4, D-9 | Keep. LR-052, note §6, I-2, LR-050 and LR-005/LR-015 are consistent with them |

## 8. Commands run (read-only)

```text
git checkout pipe/w9-wp9-1-catalogue                       # worktree beautiful-volhard-d3f62e, HEAD 479745fc
git log --oneline 4bf94d61..HEAD; git diff --stat 4bf94d61..HEAD
git diff 4bf94d61..HEAD -- docs/plans/agentic-research-system/03-decisions-and-open-questions.md
git ls-tree HEAD docs/plans/agentic-research-system/transition/w9/
git log --oneline -1 origin/main                           # still 5d325c5b
/c/Users/steph/TDL/.venv/Scripts/python.exe -I <scratchpad>/rr/probe.py <repo>   # annex parse + mechanical checks
/c/Users/steph/TDL/.venv/Scripts/python.exe -I <scratchpad>/rr/rows.py <repo> <row ids>   # full text of 35 rows
grep -n 'owner_row_id: LR-0..' / "^- 'G[345]" annex
sed -n 295,322p research_system/discovery/routes.py
sed -n 1312,1330p research_system/projection/replay.py
grep -n ResolveDecision research_system/command/service.py research_system/authority.py
sed -n 40,66p research_system/discovery/commands.py
```
