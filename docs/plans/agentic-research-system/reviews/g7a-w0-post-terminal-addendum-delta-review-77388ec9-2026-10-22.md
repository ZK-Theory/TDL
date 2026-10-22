---
document: G7-A bounded independent delta review
date: 2026-10-22
subject: transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md
subject_commit: 77388ec9
subject_blob: a5ad046ddbd20e4b8c54c9c3f570227b33ebaa81
verified_against: origin/main 3fa437a160ab75c5fa0083fd35176006b1ee19a4
verdict: REWORK REQUIRED
reviewer: independent session (adversarial-design-review), distinct from the Gate 7 prep author session
implementation_authority: none
---

# G7-A delta review: W0 post-terminal addendum (77388ec9)

## 1. Subject and basis

| Item | Value |
|---|---|
| File | `docs/plans/agentic-research-system/transition/W0-legacy-closeout-post-terminal-addendum-2026-10-21.md` |
| Commit | `77388ec9` on `claude/gate7-prep-docs-5202cf` (read with `git show 77388ec9:<path>`) |
| Blob | `a5ad046ddbd20e4b8c54c9c3f570227b33ebaa81` (18,220 bytes; `git rev-parse` / `git cat-file -s`) |
| Verified against | origin/main `3fa437a160ab75c5fa0083fd35176006b1ee19a4` after `git fetch origin` on 2026-10-22. That is still origin/main, so "current" and the observation commit are the same. |
| Tracker | `C:\Users\steph\TDL\.apm\tracker.md`, read only. Its working-copy hash `c2716092000f8cb365e5e0b51d98b75b6667fdaf` equals `origin/main:.apm/tracker.md`, so the tracker I read is the tracker at `3fa437a1`. |
| Method | `git log`/`show`/`diff`/`rev-parse`/`merge-base --is-ancestor`; `gh pr view` and `gh api .../pulls/N/reviews`; read-only reads of the tracker, Stage 1 and Stage 2 task-log headers, the vault Computational-Log (2026-07-09 to 2026-07-18 entries), CONVENTIONS, the June W0 snapshots, 03 (P-026, P-034, A-001, A-002, P-058 section), 06l §2 and §5, 06u §§2, 4, 6.1, 8 to 12, handoff 14, handoff 07, the freeze handoff §§1 to 5, and the claim-trace audit §3. Jira: KAN-20 read only (summary, description, status). |

## 2. Verdict

**REWORK REQUIRED** (bounded).

The identity layer is sound. Every commit, merge, blob, byte size, PR number and ancestry claim I checked in §2, §4,
§6, §7, §8, §10 and §11 is correct, with one factual exception (m1). The completeness check passes: §6 plus the
manifest's §5.2 cover every Stage 1 tracker row, and §8 covers all 26 Stage 2 rows, each exactly once (§5 below).
The #277 hunks under `papers/` are all behaviour-preserving.

The rework is needed because the addendum fails its own check 4 ("no statement here promotes a superseded or
unverified result"). Four mechanisms do it, and none of them is a wrong identity:

- §6 says the manifest's §5.2 classes "stand" and only adds rows. Several of those classes changed authority in the
  delta window (M1).
- The delta set leaves out the 2026-07-18 adversarial mathematical review and the audit holes. 06u §8.1 puts them in
  scope, and one finding (A2) is about T1.28's own p-values (M2).
- §9's proposed A-001 wording asserts a universal closure that known open items contradict (M3).
- §7 sends successors to `SUPERSEDED.md` for a do-not-cite boundary that the file does not record (M4).
- §8 and §9 carry the merged drafts forward as `merged_draft` and A-002 as "unchanged in substance". They do not
  account for the claim-trace audit or the §6.2 falsification and HOLD (M5).

There is also an internal class contradiction. The frozen Stage 2 tasks are labelled `deferred`, yet §5 says no
attributed decision deferred them (M6).

Counts: **Blocking 0 · Major 6 · Minor 12 · Info 5.**

No finding is Blocking, because nothing is transferred and the addendum is `review_pending`. The Majors must be
fixed before Stephen disposes the addendum, because it is the record that G7-B's legacy inventory and 06l Step 3
will consume.

## 3. Findings

Each finding gives the claim, the evidence, the failure it allows, and the correction it needs. File references are
to the subject at `77388ec9` unless another path is named. Commands ran from the worktree against origin/main
`3fa437a1`.

### Major

#### M1. §6 leaves manifest §5.2 classes standing where the delta window changed their authority

- **Claim (§6, line 85):** "The manifest's §5.2 table stands for its date. These rows are added". §12 row 3: "The
  grouped Phase 1 inventory does not promote a superseded result: Holds only with §7's supersession changes
  applied".
- **Evidence:**
  - Manifest §5.2 (origin/main, lines 136, 145 and 154) classifies T1.8, T1.26/T1.26b and T1.37 as `authoritative`.
  - **T1.26/T1.26b.** The tracker row T1.26b (line 108) rests its outcome on
    `bhps_nonoverlap_reanalysis_2026-06-09.json` (remainder d_perm −2.8545). The Computational-Log 2026-07-16
    `[DECISION]` "T1.38 outcome fork: non-overlap H1 claim falsified" and `SUPERSEDED.md` (commit `c8c6dd13`,
    restored by `c4b1897d`) record that this value is the greedy convention. The exact value is d_perm +7.48 with
    p 0.000999. The claim is "**FALSIFIED** for this retained remainder object". The claim-trace audit §3.2 says
    "The committed `bhps_nonoverlap_reanalysis_2026-06-09.json` greedy H₁ is do-not-cite".
  - **T1.8.** The tracker row (line 88) says "RA 5-lane PASS vs `markov2_alpha_sweep_summary_2026-06-16.json`" with a
    W₂-only decision rule. The T1.38 Phase 1 `[RESULT]` (Computational-Log, 2026-07-16 entry) says "That summary is
    **UNVERIFIABLE**". The 2026-07-18 adversarial review's A1 adds that the order-2 generator draws the second token
    uniformly, which makes the Markov-2 rung anti-conservative (Computational-Log 2026-07-18 `[EXPLORE]`; #132,
    merged 2026-07-20).
  - **T1.37.** The manifest calls it the "source of canonical Stage 1 headline values". `a9dcccbf` (2026-07-14) and
    the `SUPERSEDED.md` table move the H₁ W₂ blocks of both `*_headline_frozen_2026-05-28.json` files to the
    corrected 2026-07-14 files. The frozen files stay canonical only for H₀ W₂ and landscape L².
  - §7 lists those `SUPERSEDED.md` commits, but nothing maps them back to the §5.2 task rows.
- **Failure:** A successor builds the Phase 1 inventory as manifest §5.2 plus addendum §6, as §6 instructs. It then
  imports T1.26b's `size_or_fraction_artefact` outcome and T1.8's α-stability conclusion as `authoritative`. Those
  are a falsified object and a W₂ conclusion built on an UNVERIFIABLE source.
- **Required correction:** Add a "§5.2 rows whose class changed" table to §6. It should cover at least T1.8
  (`superseded` or `unverified` for its W₂ conclusion, citing T1.38 Phase 1 and A1), T1.26b (`superseded` for the
  H₁ W₂ non-overlap outcome, with landscape values standing, citing the 2026-07-16 `[DECISION]`) and T1.37 (H₁ W₂
  headline blocks superseded by the 2026-07-14 corrected files). Then re-derive every other §5.2 row against
  `SUPERSEDED.md` and claim-trace audit §3.2, and say for each row that it was checked. Until that is done, §12 row
  3 should read "Open", not "Holds".

#### M2. The delta set omits post-terminal soundness findings that 06u's accepted scope puts in it

- **Claim (§13):** "The delta set is §4 to §12 of this addendum". The scope note it implements says otherwise. 06u
  §8.1 item 1 says "Its delta set includes the §6.1 items, the merged-without-review #105 and the park-set count".
  Stephen accepted "the 06u scope" (06u §12).
- **Evidence:** 06u §6.1 lists:
  - audit holes H1 to H5 and H7 to H9 (H6 resolved by #129);
  - "H3 non-overlap L=1882 arm + 20 subsamples", open, which needs Stephen's re-run-or-drop decision;
  - "Adversarial mathematical review A1–A4, B1–B7, C1–C3", open, with A1 an owner fork.

  The addendum mentions none of these.
  - Computational-Log 2026-07-18 `[EXPLORE]`: A2 says "every production p-value (`_battery_core.py:408–431`,
    **consumed unchanged by the T1.28 stratified runner**…) compares the *mean* of B obs-null distances against
    *individual* null-null pair distances, severely conservative/uncalibrated". Its consequence line: "the Gate-7
    rewrite must not promote rung-4/5 rejection claims until the A1 fork is decided and the double-null calibration
    runs".
  - #132 merged at `0e906ad6` on 2026-07-20 and #131 (the invariant battery) at `7cdba0d0` on 2026-07-20 (`gh pr view
    131/132`). Both are post-terminal changes to the legacy research record on main.
  - 06u D-7 asks that it be recorded "now that the Markov-2 pre-reg needs an amendment either way, so nothing
    dispatches on the 2026-07-17 pre-reg as filed".
  - §4 restates T1.28's headline as `authoritative` without the A2 caveat. §6's Markov-2 row cites the 2026-07-17
    pre-registration as its basis. §16's first trigger ("T1.41 or the Markov-2 recompute is dispatched, under any
    authority") does not say that dispatch on the pre-registration as filed is barred.
- **Failure:** G7-B and G7-C take this addendum as the legacy inventory. They inherit T1.28's 12/12 and 9/11
  rejections and the Markov-2 pre-registration without the soundness caveats that the accepted scope required this
  record to carry.
- **Required correction:** Add a section for the post-terminal soundness and provenance record: #131, #132 (A1 to A4
  and B/C by pointer), and audit holes H1 to H9 with current status (H6 resolved by #129, H3 open). Give a one-line
  caveat on each affected row: T1.28 (A2), T1.8 and Markov-2 (A1), T1.41 (A3). State in §6 and §16 that the Markov-2
  recompute must not dispatch on the 2026-07-17 pre-registration without an amendment (06u D-7).

#### M3. §9's restated A-001 wording asserts a closure the author did not check and that known open items contradict

- **Claim (§9, lines 153 to 157):** "Every Stage 1 task on the tracker at `3fa437a1` is `authoritative`,
  `superseded`, `deferred` with a parked record, or `prepared`. T1.41 and the Markov-2 recompute are the only Stage 1
  items carrying open research work. No other Stage 1 computational or assurance requirement exists." The author
  adds: "The author has not checked every Stage 1 row against its evidence".
- **Evidence:**
  - A-001's confirmation condition (03, A-001) is "no additional Phase 1 computational or assurance task remains
    open".
  - Known open Stage 1-class requirements outside T1.41 and Markov-2: H3 (the L=1882 arm and 20 subsamples need a
    production re-run; 06u §6.1, audit §3.3); A2 (a recomputation of the p-value form from retained per-pair arrays;
    Computational-Log 2026-07-18); H7 ("convention-gate them or annotate immunity… before citation-grade use"; audit
    §3.3).
  - No Stage 1 task is `prepared` at `3fa437a1`, so that class in the list is vacuous.
  - T1.40's task log is `status: Partial` (`.apm/memory/stage-01/task-01-40.log.md`); the addendum classifies it
    `authoritative`.
- **Failure:** The wording is offered for a confirmer to sign. If it is signed as drafted, A-001 is confirmed on a
  statement that is false at `3fa437a1`. A-001 confirmation is one of the conditions for affected ownership
  transitions (06l §2.2 item 2, Step 3), so a false confirmation unlocks the wrong boundary. The caveat that the
  author did not check sits beside the claim but does not qualify it.
- **Required correction:** Rewrite the proposed wording to enumerate rather than close. List the open Stage 1-class
  requirements by name: T1.41, Markov-2 with its pre-registration amendment, H3, the A2 recomputation, H7, and any
  others the M1 re-derivation finds. Ask the confirmer to confirm that list as complete. Drop `prepared`. If the
  universal sentence is kept at all, it should read "No Stage 1 computational or assurance requirement exists other
  than those listed above".

#### M4. §7 sends successors to `SUPERSEDED.md` for a boundary it does not hold

- **Claim (§7, lines 114 to 117):** "two do-not-cite boundaries were added in this window: … the Markov-2 α-sweep
  summary's W₂ is `UNVERIFIABLE` (T1.38 phase 1). Any successor import must take the supersession records at
  `3fa437a1`".
- **Evidence:**
  - At `3fa437a1`, `results/trajectory_tda_integration/stage1/SUPERSEDED.md` line 69 still says that
    `markov2_alpha_sweep_summary_2026-06-16.json` is "**exact era, presumed IMMUNE**, but never explicitly gated… Confirm
    by gate before citing as verified".
  - None of the window's commits (`c8c6dd13`, `b8c9793e`, `518da347`, `c4b1897d`, `1af52f6d`) rewrites that entry. I
    read each diff of the file.
  - The UNVERIFIABLE classification lives only in the T1.38 Phase 1 `[RESULT]` in the vault, in the phase 1 result
    JSON, and in claim-trace audit H7.
  - `SUPERSEDED.md` contradicts itself on this object: the `1af52f6d` cell entry calls the summary
    "solver-uncertifiable", while line 69 says "presumed IMMUNE".
  - Manifest §8.1 makes `SUPERSEDED.md` the import source for supersession events.
- **Failure:** A successor follows §7 and the manifest import policy. It imports "presumed IMMUNE" for the summary,
  and P01-B Table 2's Markov-2 W₂ rows remain citable-pending-gate rather than do-not-cite.
- **Required correction:** Change §7 to say the UNVERIFIABLE classification is recorded in the T1.38 Phase 1
  `[RESULT]` and phase 1 JSON, not in `SUPERSEDED.md`. Record the record-level contradiction as a
  `stale_projection` of `SUPERSEDED.md` line 69. Add it to §14's stale-wording list. Name it as an import-time
  conflict that G7-B must resolve, by source precedence (manifest §8.4: a decision plus result beats the summary
  line). The frozen legacy record is not edited.

#### M5. §8 and §9 carry the merged drafts forward without the claim-trace audit or the §6.2 HOLD

- **Claims:**
  - §8 classifies T2.1 to T2.6, T2.17 and T2.18 as `merged_draft` ("Wave-1, unchanged").
  - It classifies T2.7 and T2.8 as `merged_draft` ("§6.1 and §6.2").
  - §9 says A-002 is "Unchanged in substance… the merged material keeps its authority as draft".
- **Evidence:**
  - Manifest §4 defines `merged_draft` as "Accepted and merged manuscript material".
  - Claim-trace audit (origin/main, `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md`):
    - `results-negative-control-wording.md` "**entire file invalid**", which asserts INVALID-BY-CONSTRUCTION p-values
      as evidence;
    - `table1-effects-d_perm-rho-CI.md` "**all cells unciteable**";
    - §6.2 (`results-bhps-robustness.md`) A24 "**FALSIFIED**" and A21 "Struck by the 2026-07-14 ruling";
    - A11/A17, a wrong p-value denominator against a contract-locked object;
    - "every P01-A document except §S8 carries register scaffolding" (Computational-Log 2026-07-17 entry).
  - The 2026-07-16 User ruling "HOLD §6.2" is carried forward by the freeze (`[DECISION]` 2026-07-18,
    "Supersession: none… 2026-07-16 non-overlap §6.2 HOLD").
  - Both T2.7 and T2.8 task logs are `status: Partial` (`.apm/memory/stage-02/task-02-07.log.md`, `task-02-08.log.md`).
    By manifest §8.4 precedence, task logs rank above the tracker. The tracker says Done.
  - §2's method lists only `.apm/memory/stage-01/` headers, so no Stage 2 log was read.
- **Failure:** A successor imports §6.2 and the §4.3 negative-control file as accepted draft material. That is the
  promotion of a falsified, do-not-cite claim which check 4 forbids.
- **Required correction:** Keep `merged_draft` as the class for what is merged. Add an explicit per-file qualifier
  column that points to the claim-trace audit verdicts. At minimum: §6.2 HOLD with A24 falsified and A21 struck,
  §4.3 negative-control file invalid, the Table 1 effects family unciteable, and the A11/A17 denominator. Restate
  A-002 as "merged draft material keeps its draft authority **subject to the 2026-07-17 claim-trace audit verdicts**".
  Record the T2.7 and T2.8 Partial logs as a `stale_projection` divergence. Their logs predate the User approval
  that the tracker records for T2.7. State T2.8's review state. Add `stage-02` to §2's method.

#### M6. "`deferred` (frozen)" contradicts the manifest's class definition and the addendum's own §5 and §8

- **Claim:** §8 classifies T2.9, T2.10, T2.11, T2.19, T2.20, T2.21 and T2.22 as "`deferred` (frozen)". §5 trigger 3
  says "**No**: The 2026-07-18 freeze suspends them but records 'Supersession: none'". §8 says "The freeze suspends
  the remaining Stage 2 work. It does not dispose of it".
- **Evidence:**
  - Manifest §4: `deferred` means "Explicitly removed from the current paper scope or moved to later work".
    `blocked` means "A named external input or decision prevents progress".
  - 06l Step 3's output classes include both `blocked` and `deferred`. A `deferred` disposition is what Step 3 must
    produce "by an attributed scope decision" (06l §2.2 item 3).
- **Failure:** If the class is right, an attributed decision deferred these tasks, and trigger 3 fired. If §5 is
  right, the class asserts a disposition that W0-D2 is still asking Stephen for. Either way a successor reading the
  class column sees the Stage 2 scope as already disposed. That pre-empts 06l Step 3 and W0-D2.
- **Required correction:** Reclassify them `blocked`, naming the blocker as the 2026-07-18 freeze `[DECISION]` and
  the open Stage 2 scope decision (W0-D2). Keep `deferred` only for T1.41 and Markov-2: an attributed User decision
  moved those to later work ("PARKED FOR ARS (User, 2026-07-18)"). Re-check §5 trigger 3 after the change. The
  current "No" then holds.

### Minor

#### m1. "Both `SUPERSEDED.md` files changed after 2026-06-29" is false

- **Evidence:** `git log 33ab053e..origin/main -- results/trajectory_tda_bhps/stage1/SUPERSEDED.md` returns nothing.
  The file was last changed by `a67ca4c7` on 2026-06-21. Every commit in the §7 table touches only the integration
  file.
- **Correction:** Say "Only `results/trajectory_tda_integration/stage1/SUPERSEDED.md` changed. The BHPS pointer file
  is unchanged since `a67ca4c7` (2026-06-21)".

#### m2. T2.24 and T2.17a get different classes for the same main state

- **Evidence:** Both reached main through #106 (`10095d44`, whose second parent is `8df43afa`, the T2.24 commit).
  #112 reverted both. `diff <(git diff 10095d44^1 10095d44) <(git diff f1171fd4 f1171fd4^1)` shows the two diffs
  are exact reverses. All 14 files #106 touched are byte-identical on origin/main to their pre-#106 blobs.
- **Correction:** Class T2.24 `superseded` on main, the same as T2.17a. Record the tracker row separately as a
  `stale_projection`. `stale_projection` is a class for a record, not for a task.

#### m3. The §10 description of #277 is incomplete and cites irrelevant evidence

- **Evidence:** `git diff 1dbf6b7b^1 1dbf6b7b -- papers/`, read in full:
  - `compute_table1_effects.py` removes `import numpy as np` and `from numpy.typing import NDArray`. Neither is used
    in the pre-image (grep finds them only at lines 15 and 16). The rest is reformatting: line joins, adjacent string
    literals placed on one line (the concatenated value is unchanged), `**` spacing, and one blank line before a
    nested `def`.
  - `read_jbstat_dict.py` removes `from typing import Dict` (used only at its import line) and reformats slices and
    blank lines.
  - `income_vars_check.py` renames the comprehension variable `l` to `label` (E741). That is a rename, neither
    formatting nor import removal. It is behaviour-preserving.
  - §10 also cites "the PR body states the F841 removals were checked". No hunk under `papers/` is F841. The
    removals there are F401 (PR body table: "F401 | 11 | `ruff --fix`"; "E741 | 3 | `l` renamed").
  - The post-freeze claim holds: `git log 33ab053e..origin/main` on the three paper roots shows `1dbf6b7b` as the
    only commit after #126 (`4b143c92`, merged 2026-07-18T12:19Z). The pre-freeze set #81, #106, #109, #112, #116,
    #118 is exact by `--first-parent`.
- **Correction:** Use "formatting, two unused-import removals (F401) and one E741 rename; all behaviour-preserving
  (reviewer-verified)". Drop the F841 citation.

#### m4. Post-freeze writes to other legacy surfaces are not recorded

- **Evidence:**
  - #368 (`452352ff`, 2026-10-17) appended a Working Notes entry to the frozen `.apm/tracker.md`, recording a sweep
    of 21 worktrees, including `.apm/worktrees/tamper-split`. It also names `.git/worktrees/pipe-two-machine-check`
    as held.
  - `1af52f6d` (2026-07-18T19:05, after the freeze merge) wrote `SUPERSEDED.md` and two result JSONs. #129, #131
    and #132 merged later.
  - §14 says the tracker rows "are not edited". §16 makes "any … `.apm/` tracked file … changes on main" a future
    trigger, but that trigger had already fired before the addendum was written.
- **Correction:** Widen §10 from paper roots to the legacy surfaces in manifest §8: `.apm/` tracked files,
  `SUPERSEDED.md` and the result roots. List #368 and `1af52f6d`, and note them for G7-B's path/writer registry.
  Reword §14's "are not edited" to "no Task row is edited; #368 appended a Working Note".

#### m5. §3 changes who seals W0 without a named decision

- **Evidence:** The manifest's frontmatter (`review_gate: current APM Manager and Stephen`) and §14 ("W0 is sealed
  only when the current Manager and Stephen confirm") name the sealing authority. §3's `sealed` row makes it
  "Stephen and the A-001 confirmer". W0-D1 asks only who confirms A-001. 06l Step 3 says "The Manager explicitly
  confirms or rejects A-001".
- **Correction:** Widen W0-D1 so it names the signatory for all eight §14 items, not only A-001. Route the change to
  A-001's confirmation condition and to 06l Step 3 through G7-C's register entry. KAN-20 asks for "a single coherent
  state-machine transition… with evidence and a responsible owner recorded per transition" (read 2026-10-22). Add
  the missing states (this addendum drafted and under review; addendum rejected) so that every transition has an
  owner.

#### m6. Clash 4's "binds nothing beyond §9" drops P-034's boundary

- **Evidence:** P-034's boundary: "T1.28 terminal review still gates legacy deprecation claims". P-026: "T1.28
  terminal review still triggers a W0 addendum and bounded design reconciliation". Handoff 14's one-line rule:
  "until the addendum and terminal disposition are fully confirmed".
- **Correction:** Use "T1.28 binds legacy closeout through acceptance of this addendum and its delta review (P-026)
  and gates legacy deprecation claims (P-034). After acceptance it binds only through A-001".

#### m7. Clash 1's second limb is an interpretation stated as fact

- **Evidence:** "Neither paper is active: both are suspended under the freeze". The papers remain `legacy_owned`
  (P-026, P-034), with undisposed Stage 2 scope (§8) and parked prose directions (freeze handoff §3). The point of
  the WP6.7 sentence is P-026's boundary.
- **Correction:** Use "the 'active' limb is ambiguous under the freeze. The papers are suspended, not disposed, and
  remain `legacy_owned`. G7-C's positive preconditions replace the sentence. 'Suspended' does not by itself satisfy
  P-026".

#### m8. The stale-wording list in §14 is incomplete

Projections the addendum's own evidence shows to be stale, but which the list omits:

- the tracker's T1.38 row ("`b8c9793` on `run/w2-gap-closure`, not merged"; now on main through #117);
- the T1.39 row ("not merged"; `ad65f1e` is an ancestor of main);
- the T1.41 row ("Ready"; parked);
- the T2.17a row ("not merged"; merged, then reverted);
- the T2.7 and T2.8 Partial logs against the tracker's Done;
- the T1.40 Partial log against "GATE 0 CLOSED LIVE";
- `SUPERSEDED.md` line 69 (M4);
- 03 A-002's "fourteen";
- claim-trace audit §3.3 H6 ("Not locatable"; resolved by #129).

**Correction:** add these to the list for G7-C.

#### m9. Two §6 rows describe their evidence imprecisely

- **Evidence:**
  - T1.38 Phase 1 (`c8c6dd13`) also went through #105, then #111's revert, then #117. `c8c6dd13` is an ancestor of
    both `b8c9793e` and `81cb870e`, and `518da347` removed its `SUPERSEDED.md` entry. The text implies that only
    Phase 2 did.
  - T1.40's evidence "Same branch" omits that its log is `Partial` and that the LIVE closure is the Manager addendum
    JSON (tracker row T1.40).
  - The #105 and #117 review claims hold: #105 has no reviews, and #117 has two CodeRabbit reviews (16:20Z and
    17:22Z) before its 18:44Z merge.
- **Correction:** State both facts.

#### m10. §11's attribution to P-058 is an inference

- **Evidence:** The P-058 section (03, from line 1434) does not mention legacy tasks, results or paths. The
  "nothing transferred" claim follows from the run's route scope (SPEC-01, fresh store; 06u §4), not from a
  sentence in P-058.
- **Correction:** Use "P-058's route package covers only the SPEC-01 route on a fresh store, and names no legacy
  item. This is inferred from its scope. The store was not read". The stated limit is otherwise adequate.

#### m11. §13 narrows the scope below 06l Step 2 without saying so

- **Evidence:** 06l Step 2's inputs include "the current paper and Discovery boundary". §13: "It does not cover
  Discovery items".
- **Correction:** Either cover the Discovery boundary or record the exclusion as a deviation from 06l Step 2 for
  Stephen to accept, with Discovery left to G7-B and W11.

#### m12. Two of the §5 trigger rows have weak evidence, though both dispositions stand

- **Evidence:**
  - Trigger 4 cites T1.41 and Markov-2. Neither was in the June no-migration set; the addendum adds them in §11. The
    stronger evidence is the freeze's transfer of prose production, covering the remaining Stage 2 work (a manifest
    §10.1 no-migration item), to ARS. The freeze handoff §3 says "§6.2 / §4.3 / §S6 prose directions: deferred to
    ARS".
  - Trigger 2's dates ("2026-07-14 to 2026-07-16") have no cited source. The rows for T1.38 to T1.41 first appear on
    main in `9ca20884` (2026-07-17). The T1.38 pre-registration is dated 2026-07-15.
- **Correction:** Cite the freeze for trigger 4. Cite the pre-registration and tracker dates for trigger 2.

### Info

- **i1. CONVENTIONS dating.** "The lock text predates it by a day" is approximate. The lock is labelled "locked
  2026-07-17" and its wording was approved that day (freeze handoff §5). The text itself was committed in
  `8b4183ee` at 2026-07-18T10:36, seven minutes before `4d5dde97` (10:43) added "No further APM compute Tasks are
  dispatched". The lock also cites the 2026-07-18 `[DECISION]`. The quoted wording difference is correct.
- **i2. Retained branches.** §11's branch check was local only. Remote state: `paper/p01a-dedup-rewrite`,
  `paper/p01b-methods-results`, `pipe/gate-liveness-audit` and `run/w2-gap-closure` have `[gone]` upstreams, so their
  remote branches were deleted. The local `paper/p01a-dedup-rewrite` (`8df43afa`) is an ancestor of main, so the
  park-set #106 content can be recovered from main's history whatever happens to the ref. `pipe/two-machine-check`
  (`57684e3d`) is unmerged, as stated.
- **i3. "Fourteen-plus".** Twelve of the original fourteen remain undisposed (T2.9 to T2.16, T2.19 to T2.22),
  because T2.7 and T2.8 merged. T2.16a, T2.17a and T2.24 also need a disposition. W0-D2 should name the 15 rows.
- **i4. Frontmatter status.** The addendum's own `status: review_pending` reuses the term that §3 and KAN-20 set out
  to disambiguate. Consider `review_pending (document)`, or a value from the §3 vocabulary.
- **i5. T2.12 to T2.16 as `unverified`.** This is supported. Their content reached main through #109
  (`a1b89604`). #109 is titled "de-scaffold 7 section files, zero science change (T2.23)" but adds four new methods
  files and `results-4-2-tables.md`. No Stage 2 logs exist for T2.12 to T2.16, and the User per-section review is
  outstanding. #116 and #118, which are pipe-lane PRs, later edited those files. Record that, so the `unverified`
  content on main is not mistaken for #109's bytes.

## 4. Claims verified correct

| § | Claim | Evidence |
|---|---|---|
| 2 | `3fa437a1` (#387), committed 2026-10-21T22:42:45+01:00; `33ab053e` (2026-06-29) is an ancestor and is the 06-29 addendum's `review_commit` | `git log -1`; `merge-base --is-ancestor`; 06-29 frontmatter `review_commit: 33ab053e…` |
| 4 | #72 merge `703101de…` (2026-07-09), an ancestor | `git log -1`; `gh pr view 72` |
| 4 | Blobs `b1a9dd85…` (10,485 bytes) and `a09de18d…` (9,444 bytes) at `3fa437a1`, unchanged since `34dddd37` | `git rev-parse` at both commits; `git cat-file -s`; single-commit `git log` per path |
| 4 | Task log `status: Success`, `commit: 34dddd3`, PR #72; headline 12/12 and 9/11; strata named | log header; tracker row T1.28; Computational-Log 2026-07-09 `[RESULT]` and `[DECISION]` |
| 4 | The T1.20 open item closed 2026-07-11 | Computational-Log 2026-07-11 `[DECISION]`; tracker open-threads row |
| 6 | #79 `823b40ad` 2026-07-11; `c8c6dd13`; `b8c9793e`; #105 `305a5516`; #111 `408f52bb`; #117 `e8890fb7`; `f3ccae0b` an ancestor | `git log -1`; ancestry; `gh pr view` |
| 6 | T1.41 inputs: 20 files | `ls … \| wc -l` = 20 |
| 7 | `a9dcccbf`, `ccaf79d5`, `c8c6dd13`, `b8c9793e`, `518da347`, `c4b1897d`, `1af52f6d`: dates and content as described | per-commit `git show -- SUPERSEDED.md` |
| 8 | #126 `4b143c92`; "Supersession: none"; both quoted wordings | `gh pr view 126`; Computational-Log 2026-07-18; `CONVENTIONS.md` line 47 |
| 8 | #81 `36885054`; #109 `a1b89604`; #106 `10095d44`; #112 `f1171fd4` (exact full revert); `6c128f6` | `gh pr view`; reverse-diff identity |
| 10 | The PR list before and after the freeze | `git log --first-parent 33ab053e..origin/main -- <three roots>` |
| 11 | Five bullets in the handoff against "6 items" in handoff 07 | freeze handoff §3; handoff 07 line 74 |
| 11 | `pipe/two-machine-check` (`57684e3d`) unmerged; three branches absent; four ancestors of main | `git branch -a`; ancestry |

## 5. Completeness check (item 2)

Tracker sections at `3fa437a1` (blob `c2716092`): "Stage 1" has 51 rows (lines 72 to 123); "Stage 2" has 26 rows
(lines 35 to 60). The out-of-table "Open threads" rows (T1.20, T1.6) are covered in §6. The coverage sources are
the manifest's §5.2 (M) and the addendum's §6 and §8 (A).

### Stage 1

| Tracker row(s) | Covered by | Note |
|---|---|---|
| 1.1 | M §5.2 | |
| 1.2, 1.2a–1.2f | M §5.2 (group) | |
| 1.2g | M §5.2 (with T1.7) | |
| 1.2h | M §5.2 | |
| 1.3 | M §5.2 | Not re-derived (M1) |
| 1.4 | M §5.2 | |
| 1.5 | M §5.2 ("T1.5 family") | |
| 1.6 | M §5.2 + A §6 | Updated, not doubled |
| 1.7 | M §5.2 | |
| 1.8 | M §5.2 | **Class stale (M1)** |
| 1.9, 1.9b | M §5.2 | |
| 1.10–1.19 | M §5.2 (group T1.10–T1.20) | |
| 1.20 | M §5.2 group + A §6 | Updated, not doubled |
| 1.21 | M §5.2 | |
| 1.22 | M §5.2 | |
| 1.23 | M §5.2 | |
| 1.24 | M §5.2 | |
| 1.25 | M §5.2 | |
| 1.26, 1.26b | M §5.2 | **Class stale (M1)** |
| 1.27 | M §5.2 | |
| 1.28 | A §6, §4 | Supersedes M `prepared` |
| 1.29–1.32 | M §5.2 (group) | |
| 1.33 | M §5.2 | |
| 1.34, 1.34a-redo | M §5.2 | |
| 1.35 | M §5.2 | |
| 1.36 | M §5.2 | |
| 1.37 | M §5.2 | **H₁ W₂ blocks superseded (M1)** |
| 1.38 | A §6 | Tracker order 1.39, 1.40, 1.38, 1.37 (lines 120 to 123); none missed |
| 1.39 | A §6 | |
| 1.40 | A §6 | Log Partial (m9) |
| 1.41 | A §6 | Tracker row at line 72, above 1.1 |
| (no T-number) Markov-2 recompute | A §6 | Not a tracker row; correctly flagged |

Result: no Stage 1 row is missing or doubled.

### Stage 2

| Tracker row(s) | Covered by (A §8) | Note |
|---|---|---|
| 2.1–2.6 | "T2.1–T2.6, T2.17, T2.18" | Claim-trace qualifiers missing (M5) |
| 2.7, 2.8 | "T2.7, T2.8" | Logs Partial; §6.2 HOLD (M5) |
| 2.9 | "T2.9" | Class (M6) |
| 2.10, 2.11 | "T2.10, T2.11" | Class (M6) |
| 2.12–2.15 | "T2.12–T2.15" | `unverified` supported (i5) |
| 2.16, 2.16a | "T2.16, T2.16a" | |
| 2.17a | "T2.17a" | Tracker line 52, above 2.17 |
| 2.17, 2.18 | first row | |
| 2.19 | "T2.19" | Class (M6) |
| 2.20, 2.21 | "T2.20, T2.21" | Class (M6) |
| 2.22 | "T2.22" | Class (M6) |
| 2.23 | "T2.23" | |
| 2.24 | "T2.24" | Class (m2) |

Result: 26 of 26 rows, each covered once. The odd numbering (2.16a, 2.17a, 2.23, 2.24) is all present. The "at least
twenty-six" count in §8 is in fact exactly 26.

## 6. The specific attack items

- **§3 state sequence.** It is coherent with manifest §15 ("PARTIAL") and with §14 being unchecked. It meets KAN-20's
  ask in part: there is a per-state owner and evidence. It falls short in two ways: the sealing owner silently
  changed, and the review and rejection states are missing (m5).
- **§9's A-001 wording.** It cannot be confirmed as drafted, and it smuggles in an unchecked universal closure (M3).
- **§8 classes.** `unverified` for T2.12 to T2.16 is supported (i5). `stale_projection` for T2.24 is the wrong kind of
  class (m2).
- **§11 "nothing transferred".** The conclusion is plausible. The cited authority is an inference (m10), and the
  limit (store not read) is stated honestly.
- **Vault-citing claims.** Every Computational-Log citation in the addendum resolves to an entry of that date and
  kind: 2026-07-09 `[RESULT]`/`[DECISION]`, 2026-07-11 `[DECISION]`, 2026-07-16 `[NEGATIVE]`, 2026-07-17
  pre-registration, 2026-07-18 H6 `[DECISION]` and the 2026-07-18 freeze `[DECISION]`. What is missing is the
  2026-07-18 `[EXPLORE]` adversarial review entry (M2), and the 2026-07-16 outcome-fork `[DECISION]` with its
  User HOLD, which bears on M1 and M5.
- **Clash dispositions (§14).** Clash 1 is overstated (m7). Clash 2 is correct. Clash 3 is correct, delegated to
  G7-C. Clash 4 is overstated (m6).

## 7. Owner decisions W0-D1 to W0-D3 (reviewer opinion)

These are my opinions as reviewer. They are not dispositions.

- **W0-D1 (who confirms A-001).** I agree that Stephen should confirm it rather than a nominal new Manager. I would
  attach three conditions:
  1. Widen the decision to name the signatory for all of manifest §14 (m5).
  2. Record the change to A-001's confirmation condition and to 06l Step 3 ("The Manager explicitly confirms") as a
     register amendment through G7-C.
  3. Confirm only the M3-corrected, enumerated wording, after an independent check that covers more than §6 against
     the tracker. The check must also cover the M1 re-derivation and the M2 open items.
- **W0-D2 (when the Stage 2 scope is decided).** I agree: at 06l Step 3, not now. This holds only if M6 is fixed. With
  the frozen tasks labelled `deferred`, the addendum would already be answering the question it defers.
- **W0-D3 (accept the §3 state sequence).** Accept after m5's corrections. That means the sealing signatory is made
  consistent with W0-D1, and the drafted, under-review and rejected states are added.

## 8. Revision plan

1. **Immediate corrections (author):**
   - M1, M2, M3, M4, M5 and M6;
   - m1, m2, m3, m4, m8, m9, m10 and m12;
   - i3.
2. **Owner decisions (Stephen):**
   - W0-D1 as widened (m5);
   - accepting the m11 scope deviation, or else covering Discovery;
   - the m7 reading of "active" (G7-C).
3. **Later-work dependencies:**
   - G7-B resolves the `SUPERSEDED.md` import conflict (M4) and takes m4's writer list into its path/writer
     registry.
   - G7-C carries the stale-wording list (m8), the amendment to A-001's confirmation condition and the replacement
     WP6.7 wording.
4. **Re-review:** A focused re-review of the reconciled revision is needed for the Majors. Re-checking the identity
   table is not needed unless new identities are added.

## 9. Limits

- **Same model family.** I ran on Claude Opus 5.5, the same model family as the author session. The independence
  here is session independence, not model-family diversity (a P-058 known limit).
- **Not read:**
  - the paper drafts under `papers/P01-A-JRSSA/` and `papers/P01-B-JRSSB/`, beyond `git diff` of #277, #106, #109,
    #116 and #118 at stat level, and #277 in full;
  - any ARS store, including `TDL-ARS-G6-Control`;
  - `.apm/plan.md`, so the "twenty-two" Plan count is carried from the manifest;
  - Jira beyond KAN-20.
- **Read in part:**
  - the vault Computational-Log, 2026-07-09 to 2026-07-18 entries only, plus targeted searches;
  - Stage 1 and Stage 2 task logs, headers and summaries only.
- **M1 is not exhaustive.** I proved three stale §5.2 classes (T1.8, T1.26/T1.26b, T1.37). I did not re-derive the
  other §5.2 rows. T1.3 in particular, which cites the frozen 2026-05-29 stratified battery, is unchecked. The full
  sweep is the author's correction.
- **Not re-verified at line level:** the claim-trace audit and the 2026-07-18 adversarial review. I cite their
  recorded verdicts as the governing record. I did not check them against code or drafts.
- **No edits.** I edited no file other than this report, and committed nothing.

## 10. Observer notes (for the research-observer log; not written there, because this task allows one file)

- **RECORD / registry.** The supersession import source (`SUPERSEDED.md`) can fall behind a later `[RESULT]` that
  reclassifies an object. Here, the T1.38 Phase 1 UNVERIFIABLE classification never reached the file, which still
  says "presumed IMMUNE". The candidate rung is a contract that any `[RESULT]` or `[DECISION]` naming a file listed in
  `SUPERSEDED.md` must land a matching `SUPERSEDED.md` hunk in the same PR.
- **PROCESS.** An "X stands for its date; these rows are added" addendum pattern leaves stale classes on the rows
  that were not re-added (M1). A currency addendum should re-derive every row of a table it extends, or mark each row
  "not re-checked".
