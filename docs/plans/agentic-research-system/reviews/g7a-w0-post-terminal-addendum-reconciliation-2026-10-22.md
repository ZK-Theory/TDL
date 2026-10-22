---
document: G7-A reconciliation of the independent delta review
date: 2026-10-22
review: reviews/g7a-w0-post-terminal-addendum-delta-review-77388ec9-2026-10-22.md (committed 73d73357)
review_subject: transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md at 77388ec9 (revision 1)
reconciled_subject: the same file, revision 2 (8988f463) and revision 3 (§5; the commit that adds §5)
author: the Gate 7 prep session (the addendum's author; not the reviewer)
status: author reconciliation; not acceptance
---

# G7-A reconciliation: W0 post-terminal addendum, revision 2

Stephen directed this reconciliation on 2026-10-22: "fix M1–M6 and the listed minors in a new revision, propose the
widened W0-D1 and the Discovery scope deviation, then arrange the focused re-review."

Author reconciliation is not acceptance. Revision 2 goes to a focused independent re-review of the Majors, then to
Stephen's disposition. Section references below are to revision 2 unless marked r1.

## 1. Disposition of every finding

| Finding | Disposition | Where in revision 2 | Note |
|---|---|---|---|
| **M1** §5.2 classes left standing | **Fixed** | §6.1 (every manifest §5.2 row re-derived), §13 row 3 | Four rows change class: T1.8, T1.26/T1.26b and T1.37, as the reviewer found, and **T1.3**, which the reviewer left unchecked. T1.3's canonical source (`stratified_markov1_W2_L5000_frozen_2026-05-29.json`) is not classified by the WT-6 audit and carries the date on which WT-6 proved a sibling file greedy. Its H₁ W₂ is now `unverified`. The re-derivation also found that T1.20's closure traced §4.5 to Tier 1/2 files that audit §3.2 lists as not to cite; recorded as a note, not re-checked. §13 row 3 now reads "Holds only with §6.1 applied … Open until the signatory confirms §6.1". |
| **M2** soundness record missing | **Fixed** | §7 (new), §4 caveat, §6.2 T1.41 and Markov-2 rows, §17 | #131 and #132 recorded, with A1 to A4 by pointer and B/C by pointer; holes H1 to H9 with status; the A2 caveat on T1.28; the bar on dispatching the Markov-2 recompute on the 2026-07-17 pre-registration as filed (06u D-7). |
| **M3** A-001 wording asserts unchecked closure | **Fixed** | §10 | The wording now enumerates eight open Stage 1 requirements (T1.41, Markov-2 with amendment, A1 fork, A2, H3, H7, the T1.3 source, T1.40) and closes only "other than those listed above". `prepared` dropped. The author's limit is restated. |
| **M4** `SUPERSEDED.md` does not hold the boundary | **Fixed** | §8, §15 stale list | The UNVERIFIABLE classification is attributed to the T1.38 Phase 1 `[RESULT]`, `w2_gap_closure_phase1_2026-07-16.json` (`phase1.markov2_alpha_sweep.classification`, verified) and H7. Line 69 is recorded as a `stale_projection`, named as an import-time conflict for G7-B, resolved by manifest §8.4 precedence. Not edited. |
| **M5** merged drafts without audit verdicts | **Fixed** | §9 (qualifier column and audit-verdict list), §2 method | A-002 restated as "subject to the 2026-07-17 claim-trace audit verdicts and the §6.2 HOLD". T2.7 and T2.8 Partial logs recorded; T2.8 marked HOLD. `stage-02` added to the method. The task-to-file mapping is stated as by section title, not checked. |
| **M6** `deferred` asserted for undisposed tasks | **Fixed** | §9 | T2.9–T2.11 and T2.19–T2.22 are `blocked`, naming the freeze `[DECISION]` and W0-D2 as blockers. `deferred` is kept only for T1.41 and Markov-2 (attributed User decision, 2026-07-18). §5 trigger 3 stays "No" and is now consistent. |
| m1 both `SUPERSEDED.md` files | **Fixed** | §8 | Only the integration file changed; the BHPS pointer is unchanged since `a67ca4c7` (verified). |
| m2 T2.24 class | **Fixed** | §9, §15 | T2.24 `superseded` on main, like T2.17a; the tracker row is listed separately as a `stale_projection`. |
| m3 #277 description | **Fixed** | §11 | F401 and E741 named; the F841 citation dropped; the reviewer's full-diff verification is credited. |
| m4 other post-freeze legacy writes | **Fixed, extended** | §11 | #368 and `1af52f6d` recorded as the reviewer found. The author also found **#215** (`5df0c001`, 2026-08-05, an ARS WP6.4 PR) rewriting seven legacy result files. `git diff -w --ignore-cr-at-eol` is empty (line endings only), and `3bfb279c` restored every file to its earlier blob; the net effect is nil, verified by blob equality. §15's "not edited" reworded. §17's `.apm/` trigger now excludes the already-recorded writes. |
| m5 sealing authority changed silently | **Fixed** | §3, §16 W0-D1 | §3 keeps the manifest's named authority and routes the change through W0-D1 and G7-C. The addendum's own states (`drafted`, `under_review`, `rework_required`, `rejected`, `accepted`) are added, each with an owner. W0-D1 widened to all eight §14 items. |
| m6 clash 4 drops P-034 | **Fixed** | §15 clash 4 | The reviewer's wording, adopted. |
| m7 clash 1 "active" limb | **Fixed** | §15 clash 1 | Reworded as ambiguous under the freeze; "suspended" does not satisfy P-026. The reading itself is left to G7-C, as the review's revision plan says. |
| m8 stale-wording list incomplete | **Fixed** | §15 | Now a table of fourteen records, including all nine the reviewer listed. |
| m9 §6 evidence imprecise | **Fixed** | §6.2 | T1.38 phase 1 and phase 2 both went through #105, #111 and #117. T1.40 is now `unverified`, with the Partial log against the tracker's LIVE claim. |
| m10 "per P-058" is an inference | **Fixed** | §12 | Reworded as inferred from the route package's scope. |
| m11 Discovery excluded without saying so | **Proposed as a deviation** | §14, §16 W0-D4 | Stephen asked for this to be proposed. Recommendation: accept, with the Discovery inventory assigned to G7-B against W11. |
| m12 weak trigger evidence | **Fixed** | §5 | Trigger 4 cites the freeze's transfer of prose production. Trigger 2 cites the 2026-07-15 pre-registration and `9ca20884` (2026-07-17), both verified. |
| i1 CONVENTIONS dating | **Adopted** | §9 | `8b4183ee` (10:36) and `4d5dde97` (10:43) cited, both verified. |
| i2 remote branches | **Adopted** | §12 | |
| i3 "fourteen-plus" | **Adopted** | §9, §13, §16 | Fifteen rows named. |
| i4 frontmatter status | **Adopted** | frontmatter, §3 | Status is now `under_review`, a value from §3's own vocabulary. |
| i5 #109 bytes | **Adopted** | §9 | #109's scope and the later #116/#118 edits recorded. |

No finding is rejected.

## 2. Owner decisions after reconciliation

| ID | Change from revision 1 |
|---|---|
| W0-D1 | **Widened** (m5): the signatory for all eight manifest §14 items, with the independent check covering §6.1, §7 and §10's list. |
| W0-D2 | Unchanged; now names fifteen rows. Valid because M6 is fixed. |
| W0-D3 | Now covers both state sequences in §3. |
| W0-D4 | **New** (m11): accept the Discovery-boundary exclusion as a deviation from 06l Step 2. |

The reviewer's remaining revision-plan items for later documents are carried, not done here: G7-B resolves the
`SUPERSEDED.md` import conflict and takes §11's writer list into its path/writer registry; G7-C carries §15's
stale-projection list, the amendment to A-001's confirmation condition and 06l Step 3, and the replacement WP6.7
wording.

## 3. What the focused re-review should check

1. Each Major is fixed as stated in §1, without a new promotion of a superseded or unverified result.
2. §6.1: that every manifest §5.2 row is present, and that the four class changes (including the new T1.3 finding)
   follow from the evidence cited.
3. §10's enumerated A-001 list: complete against §6, §7 and §9, and confirmable as worded.
4. §11's #215 claim: the whitespace-only diff and the blob restoration.
5. Any new identity introduced in revision 2 (the reviewer's identity table need not be re-run otherwise).

## 4. Author's limits

- The author re-derived classes from the supersession and audit records. It did not re-match artefact values.
- The task-to-draft-file mapping in §9 is by section title.
- Same model family as the reviewer (a P-058 known limit).

## 5. Revision 3: the focused re-review of revision 2

Re-review: `reviews/g7a-w0-post-terminal-addendum-re-review-8988f463-2026-10-22.md` (committed unchanged as
`c7ef464b`), REWORK REQUIRED (narrow), 0 Blocking, 2 Major, 3 Minor, 4 Info. Stephen directed revision 3 on
2026-10-22 and authorized a read-only `git show` read of the P01-A §4.5 draft for R2. No finding is rejected.

| Finding | Disposition | Where in revision 3 | Note |
|---|---|---|---|
| **R1** A-001 list incomplete | **Fixed** | §10 items 9–12 | A4 (pinned-α_max triage), H9 (re-derive or drop), T1.8's W₂ α-stability (exact α-sweep or drop) and B1–B7 as one item scoped by the signatory. Class C is stated as prose-lane work. H10 is not a list item because it resolved as a record error. |
| **R2** §4.5 NS-SEC conflict | **Fixed and resolved** | §6.1 T1.10–T1.20 row, §7 (H10), §9 T2.1–T2.6 row, §15 | The author read `papers/P01-A-JRSSA/drafts/sections/results-escape-regression-foo.md` at origin/main with `git show`. Its table carries the canonical values: Tier 1 OR 1.0455 (p 0.8106) and 1.2161 (p 0.3073), Tier 2 1.0487/1.2324, headline 1.0954/1.1126. The canonical `tier1_clustered_firth_2026-05-16.json` gives 1.0455 (p_firth 0.81056) and 1.2161 (0.30726); the 05-13 file gives 0.8351 (0.0008) and 0.8949 (0.0466), all verified by JSON extraction. **The draft is right; the 2026-07-11 T1.20 `[DECISION]` quotes the stale 05-13 Tier 1 values.** Its exposure conclusion stands for the 05-16 file. The note's overstatement about the Tier 2 05-14 file is corrected. H10 is recorded as resolved, and a dated Computational-Log correction entry is written instead of editing the decision. |
| N1 #215 writer | **Fixed** | §11 | `5df0c001` is a direct push with no PR (one parent `a426b731`; GitHub associates no PR; verified). #215 merged as `a426b731` and touched no legacy path (verified with `git diff --name-only b21640de a426b731`). |
| N2 contracts surface | **Fixed** | §11 "Contracts" | #168 (`f523b1e5`, `b18a5222`) and #169 (`f5c449ad`, `73d58759`), attributed by the GitHub API; `811d5a2b` (no PR) and its #219 restoration (input-provenance diff empty since `4b143c92`, verified); #334. |
| N3 A32 | **Fixed** | §4 | BHPS 8/11 under the dual-metric reading. |
| I1 T1.3 Outcome A on H₀ | **Adopted** | §6.1 T1.3 row | Verified: `significant_regimes` equal the H₀-rejecting regimes, and every H₁ rejection coincides with an H₀ rejection. |
| I2 truncate arm evidence | **Adopted** | §6.1 T1.2g/T1.7 row | Verified in WT-6's `era_boundary` (6.6314 vs exact 6.6695 vs greedy 203.22). |
| I3 mislabelled source | **Adopted** | §9 | The A1 conditioning item moved under its own heading; the audit's MISDESCRIBED rows for that file kept. |
| I4 #219 | **Adopted** | §11 | `3bfb279c` cited with #219 (merge `b132406e`). |
| Reviewer opinion on W0-D4 | **Adopted into the proposal** | §16 W0-D4 | The condition that no Discovery item takes a 06l Step 3 or later action until G7-B's Discovery inventory is accepted. |

The narrow re-check the re-review scoped: §6.1's T1.20 row (and the T1.3 and T1.2g/T1.7 rows touched by I1 and I2),
§7, §9's §4.5 qualifier, §10 and §11. §4's A32 line and §16's W0-D4 condition are also new.
