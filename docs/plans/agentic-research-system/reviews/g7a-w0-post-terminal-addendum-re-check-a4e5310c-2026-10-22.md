---
document: G7-A narrow independent re-check (revision 3)
date: 2026-10-22
subject: transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md
subject_commit: a4e5310c
subject_blob: 1ebcf96ff07127561402873a52dd6a7280aa9700
reconciliation_record: reviews/g7a-w0-post-terminal-addendum-reconciliation-2026-10-22.md §5 (same commit)
prior_reviews: delta review at 73d73357 (revision 1); re-review at c7ef464b (revision 2)
verified_against: origin/main 3fa437a160ab75c5fa0083fd35176006b1ee19a4
verdict: PASS
reviewer: the independent session that wrote both prior reviews (distinct from the author session)
implementation_authority: none
---

# G7-A re-check: revision 3 (a4e5310c)

## 1. Subject and basis

| Item | Value |
|---|---|
| File | `docs/plans/agentic-research-system/transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md` |
| Commit | `a4e5310c` (read with `git show a4e5310c:<path>`) |
| Blob | `1ebcf96ff07127561402873a52dd6a7280aa9700` (42,095 bytes) |
| Verified against | origin/main `3fa437a1`. After `git fetch origin` on 2026-10-22, origin/main has not moved. |
| Method | `git diff 8988f463 a4e5310c` on the subject, read in full. I checked each changed passage against the repository, the GitHub API, the vault Computational-Log (read only), and the one authorized draft. |
| Scope | As the re-review's §7 set it: §6.1 (the T1.20, T1.3 and T1.2g/T1.7 rows), §7 (H10), §9 (the §4.5 qualifier and the relabelled A1 item), §10 (items 9–12 and the closing sentence) and §11 (the `5df0c001` attribution and the Contracts bullet). Also the new §4 A32 line and §16's W0-D4 condition. The diff confirms that nothing outside these passages changed, apart from the frontmatter revision line, §1's revision note, §2's "Not read" row, §14's verdict list and §17's trigger line. I checked those too. |
| Draft read | `papers/P01-A-JRSSA/drafts/sections/results-escape-regression-foo.md` only, at origin/main (blob `1268dfa70066f369e54fb06dc26a00e26714f5d9`, last changed in `08689307`), read with `git show`. I read no other draft file. |

## 2. Verdict

**PASS.** Every finding from the re-review of revision 2 is closed, and each closing claim matches the evidence. The
one new fact, that the §4.5 draft carries the canonical values, is confirmed by direct reading. The H10 resolution
("record error, no draft defect") follows from it. No new Blocking, Major or Minor finding. Two Info notes follow.

Counts for this re-check: **Blocking 0 · Major 0 · Minor 0 · Info 2.**

## 3. Closure table

| Finding | Status | Evidence |
|---|---|---|
| **R1** A-001 list incomplete | **Closed** | §10 adds items 9–12. Item 9 is A4, and it matches the review's §5 priority map action "Pin α_max per cell; one-cell sensitivity triage first". Item 10 is H9, matching audit §3.3 "Re-derive with referent recorded, or drop the numeric anchor". Item 11 is T1.8's W₂ α-stability across α ∈ {0, 0.5, 1, 5}, with the reason that items 2 and 6 do not cover it. Item 12 is B1–B7 as one item for the signatory to scope. The text after the list says why H10 (resolved) and class C (prose lane) are excluded. Measured against §6.1's `unverified` and `superseded` cells, §7's open holes and review findings, and §9, I find no open Stage 1 computational or assurance item missing. The closing sentence can stand as worded. |
| **R2** §4.5 NS-SEC conflict | **Closed (resolved)** | Draft lines 13–15 at origin/main read, for Tier 1, "OR = 1.0455, p = 0.8106 \| OR = 1.2161, p = 0.3073"; for Tier 2, "OR = 1.0487, p = 0.8076 \| OR = 1.2324, p = 0.3026"; and for the headline, "OR = 1.0954 … OR = 1.1126". These are the canonical values: the 2026-05-16 Tier 1 file, which I checked in the re-review, and the Tier 2 05-14 file. The draft's Tier 1 row also states n 6,173 and the "first-window R2/R6 starters" frame, which is the 05-16 window-based definition. So the draft is right, and the 2026-07-11 `[DECISION]`'s Tier 1 quotation is the stale record. The §6.1 T1.20 note is now accurate on all points: only the Tier 1 trace is to a do-not-cite file, the Tier 2 05-14 file is canonical, and the exposure argument holds for 05-16. The vault correction entry that §7 and §15 cite exists at the top of the Computational-Log ("2026-10-22 -- P01-A: CORRECTION to the 2026-07-11 T1.20 [DECISION] …"). It supersedes only the Tier 1 numbers and leaves the original entry unedited (log line 2535 unchanged). The §9 T2.1–T2.6 qualifier and the §15 stale-projection row agree with it. |
| **N1** #215 writer misidentified | **Closed** | §11 now attributes the rewrite to `5df0c001`, a single-parent commit (`a426b731`) that reuses #215's message and has no associated PR. #215 merged as `a426b731` and touched no legacy path. I verified all of this in the re-review. The restoration is cited as `3bfb279c` in #219 (merge `b132406e`, an ancestor of origin/main; verified). |
| **N2** contracts surface omitted | **Closed** | The new Contracts bullet attributes each post-freeze contract edit correctly; I checked each with `git log 4b143c92..origin/main -- <file>` and the GitHub commit→PR API. `f523b1e5` and `b18a5222` belong to #168 (merged 2026-07-26T01:59Z). `f5c449ad` and `73d58759` belong to #169 (merged 2026-07-26T11:43Z). `monte-carlo-permutation-p-value.yaml` is edited only by #169's commits. `research-assurance.yaml` and `markov-order-provenance-json-validation.yaml` are edited only by `f523b1e5`. `811d5a2b` has no associated PR (the API returns 0), and the input-provenance diff since `4b143c92` is empty. `eba3fe69` is #334. |
| **N3** A32 missing from §4 | **Closed** | §4 now carries the counting note: the W₂-only 1940s cohort (W₂ p_adj 0.016, landscape p 0.148), giving 8/11 under the dual-metric reading. This matches audit row A32. |
| **I1** T1.3 Outcome A on H₀ | **Closed** | The §6.1 T1.3 row states the H₀-only derivation with the regime sets I computed. The added sentence "the tracker's 'USoc 5/7, BHPS 8/8' describes the superseded 2026-05-13 battery" is verified: `stratified_markov1_battery_2026-05-13.json` has `per_dataset` USoc 5 of 7 and BHPS 8 of 8, Outcome A. |
| **I2** truncate-arm evidence | **Closed** | The §6.1 T1.2g/T1.7 row cites WT-6's natural experiment (6.6314 committed against 6.6695 exact and 203.22 greedy). It correctly limits the first13 arm to the day-level boundary. |
| **I3** mislabelled source | **Closed** | §9 now lists `methods-3-2-ladder-markov.md` under the audit as "two MISDESCRIBED rows". These are audit rows B9 and B10, verified: B9 is "MISDESCRIBED (major)" and B10 is MISDESCRIBED. The A1 conditioning item moved under its own heading, "From the adversarial mathematical review, not the audit". |
| **I4** #219 not cited | **Closed** | Cited in §11 with merge `b132406e`. |
| W0-D4 condition | **Adopted as worded** | §16 W0-D4 now carries the condition the re-review's §6 proposed. No Discovery item may take a 06l Step 3 or later action until G7-B's Discovery inventory is accepted. |

The passages outside the scope that changed are consistent with the rest of the document:

- §2's "Not read" row names the one authorized draft read.
- §14 records the revision 2 verdict, committed `c7ef464b`. That is verified by `git log`, which shows the commit
  "G7-A focused re-review of revision 2, REWORK REQUIRED (narrow)".
- §17 adds A4, the B1–B7 scope and H9 as triggers, which matches the §10 additions.

## 4. New findings

### Info

- **I-a. Record the draft's blob.** §2 and §6.1 say the §4.5 draft was read at origin/main but give no blob. H10's
  resolution rests on that read, so record `1268dfa70066f369e54fb06dc26a00e26714f5d9` (`results-escape-regression-foo.md`
  at `3fa437a1`) in §6.1 or in the H10 row. A later reader can then re-verify the same bytes. This is optional and
  does not change the verdict.
- **I-b. Who corrected what.** The vault correction entry was written by the author session, which is the session the
  addendum governs. Its content is a factual quotation, and I verified it independently against the committed JSON
  and the draft. So the self-correction raises no attestation concern. It is noted here so that the provenance of H10's
  "corrected" status is visible: the correction's author is the addendum's author, and the verifier is this session.

## 5. Owner decisions (reviewer opinion, unchanged)

My opinions from the re-review stand. W0-D1, W0-D2 and W0-D3: agree. W0-D4: accept. Its condition is now in the
proposal as I worded it.

## 6. Limits

- **Same model family.** I ran on Claude Opus 5.5, the same model family as the author. I wrote both earlier reviews,
  so this re-check verifies the closure of my own findings. Independence from the author is session independence
  only (a P-058 known limit).
- **One draft only.** I read one draft file (§4.5), as authorized, and no other. I did not check the rest of that
  file's claims, beyond the table rows that bear on H10.
- **Narrow scope.** I re-checked only the passages listed in §1. The identities and classes checked in the two earlier
  reviews were not re-run, except where revision 3 touched them.
- **No edits.** I wrote only this file. I committed nothing, and I wrote nothing to `.apm/`, the vault, any ARS store
  or Jira.
