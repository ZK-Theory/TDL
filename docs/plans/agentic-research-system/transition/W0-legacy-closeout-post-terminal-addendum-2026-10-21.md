---
document: W0 legacy closeout post-terminal addendum
date: 2026-10-21
baseline_manifest: W0-legacy-closeout-transition-manifest-2026-06-28.md
prior_addendum: W0-legacy-closeout-transition-addendum-2026-06-29.md
observation_commit: 3fa437a1
status: review_pending
gate7_item: G7-A (06u §8.1; Jira KAN-15, with KAN-20, KAN-23, KAN-24)
implementation_authority: none
---

# W0 Legacy Closeout Post-Terminal Addendum — 2026-10-21

## 1. Additive status

This addendum records what changed in the legacy boundary after T1.28 reached its terminal disposition. It is the
"dated W0 addendum and bounded delta review" that 04-plan §2 and P-026 require, written in the Gate 7 documentation
track under 06u decision D-4 (Stephen, 2026-10-21).

It does not rewrite the 2026-06-28 manifest or the 2026-06-29 addendum. Those remain the record of what was
established on their dates. It does not seal W0, confirm A-001, decide the Stage 2 scope, migrate any legacy item,
open Gate 7 or authorize any dispatch. Its own status is `review_pending` until the independent delta review (§13)
and Stephen's disposition.

## 2. Observation identity

| Item | Value |
|---|---|
| Observation commit | origin/main `3fa437a1` (#387), committed 2026-10-21T22:42:45+01:00 |
| Prior observation | `33ab053e` (2026-06-29), the 2026-06-29 addendum's review commit, an ancestor of `3fa437a1` |
| Method | read-only: `git` ancestry, blob and log queries against origin/main; `gh pr view`; `.apm/tracker.md` and `.apm/memory/stage-01/` task-log headers; the vault Computational-Log; `CONVENTIONS.md` |
| Not read | `papers/P01-A-JRSSA/` and `papers/P01-B-JRSSB/` draft files (out of this track's bounds); any ARS store |
| Author | the Gate 7 prep session (06u). The author does not establish its own delta verdict (§13). |

## 3. The W0 series as one state sequence (KAN-20)

The W0 documents carry two different `status` values, `review_pending` (the manifest) and `current_state_addendum`
(the first addendum). They describe different things: the manifest's status is the state of its §14 review gate,
and the addendum's is a document kind. This addendum states the series' state explicitly.

| State | Entered by | Evidence | Owner |
|---|---|---|---|
| `open_partial` | 2026-06-28 manifest | Manifest §15 outcome "PARTIAL — manifest complete, legacy boundary not sealed"; §14 unchecked | The then-current APM Manager and Stephen |
| `open_partial` (unchanged) | 2026-06-29 addendum | Additive observation; §14 still unchecked | Same |
| `post_terminal_recorded` | **This addendum, on acceptance** | §4 to §11 below; the independent delta verdict (§13); Stephen's disposition | Stephen; the reviewer for the verdict |
| `sealed` | A later decision, not this addendum | Every §14 item in §12 below resolved, A-001 confirmed by the authority W0-D1 names, Stage 2 scope decided (W0-D2) | Stephen and the A-001 confirmer |

The manifest's own `status: review_pending` stays as written. It is a snapshot field, and this table supersedes it as
the series' current state.

## 4. T1.28 terminal record (KAN-24)

T1.28 is `authoritative` and terminal.

- **Merge:** PR #72, merge `703101de6a9ebbdeb7aa56620b87f61dcbe43ce1` (2026-07-09), an ancestor of `3fa437a1`.
- **Result blobs at `3fa437a1`, unchanged since their producing commit `34dddd37`:**
  - `results/panel_methodology/fdr/stratified_w2_recompute_2026-07-09.json`: blob
    `b1a9dd8510bcfe16cce4c521ca90016dad3d3deb`, 10,485 bytes;
  - `results/panel_methodology/fdr/stratified_w2_bh_per_family_2026-07-09.json`: blob
    `a09de18d9b1719f4732cee3c854dc10f660ff8e8`, 9,444 bytes.
- **Task log:** `.apm/memory/stage-01/task-01-28.log.md` exists, `status: Success`, `commit: 34dddd3`, PR #72.
- **Headline (from the tracker row and the 2026-07-09 `[RESULT]`):** USoc 12/12 subgroups reject H₀; BHPS 9/11. The
  two non-rejecting BHPS strata (`nssec/Professional-Managerial`, `cohort/1980s`) are the pre-registered
  underpowered smallest cells. The §6.1 contingency was checked and locked by the Manager the same day.
- **The open item it carried:** "T1.20 BHPS regression may have consumed parental-NSSEC=NaN" was audited and closed
  on 2026-07-11: no v2 exposure, no rerun (Computational-Log 2026-07-11 `[DECISION]`; tracker row T1.20 RESOLVED).
  The T1.28 row's own text still says "Open (carried…)". That line is a `stale_projection`.

The 2026-06-29 addendum's §3 ("T1.28 therefore remains active, incomplete") is superseded by this section. Its
historical observation stands for its date.

## 5. The 2026-06-29 currency triggers

The 2026-06-29 addendum §7 named four triggers for a further addendum. Three have fired:

| Trigger | Fired | Evidence |
|---|---|---|
| T1.28 produces a final artefact or terminal Task log | **Yes**, 2026-07-09 | §4 |
| The Manager changes the Phase 1 scope statement | **Yes**, 2026-07-14 to 2026-07-16 | T1.38, T1.39, T1.40 and T1.41 were added after T1.28 (§6) |
| The fourteen unresolved Stage 2 tasks are accepted, deferred, removed or superseded through an attributed scope decision | **No** | The 2026-07-18 freeze suspends them but records "Supersession: none" (§8) |
| An active no-migration item is proposed for ARS adoption | **Yes**, 2026-07-18 | The freeze parked T1.41 and the Markov-2 recompute "for ARS" (§7) |

## 6. Stage 1 (Phase 1) delta

The manifest's §5.2 table stands for its date. These rows are added:

| Task | W0 class now | Evidence |
|---|---|---|
| T1.6 CodeRabbit follow-up | `authoritative` | PR #79, merge `823b40ad` (2026-07-11). Closes the review gap the 2026-06-29 addendum left open. |
| T1.20 parental NS-SEC audit | `authoritative` (closed) | Computational-Log 2026-07-11 `[DECISION]`; tracker row T1.20 |
| T1.28 | `authoritative` | §4 |
| T1.38 W2 gap closure (phases 1 and 2) | `authoritative` | Task log `task-01-38.log.md` `status: Success`. Phase 1 `c8c6dd13`; phase 2 `b8c9793e`, first merged by #105 (`305a5516`) without a CodeRabbit review, reverted by #111 (`408f52bb`), and re-landed by #117 (`e8890fb7`, 2026-07-17) with CodeRabbit review. The content on main is #117's. |
| T1.39 blob-hash signature repair | `authoritative` (infrastructure) | Branch `pipe/gate-liveness-audit` (`f3ccae0b`) is an ancestor of main |
| T1.40 Gate 0 liveness | `authoritative` (infrastructure) | Same branch |
| T1.41 double-null calibration panel | `deferred` (parked for ARS) | Freeze handoff §2 item 4; 2026-07-18 `[DECISION]`. Never run. Inputs on disk at `scratch/w2_fallback_audit/phase2_checkpoints/2026-07-16/` (20 files, 2026-10-21) |
| Markov-2 α=1 exact-W₂ recompute | `deferred` (parked for ARS) | 2026-07-17 pre-registration; 2026-07-18 H6 `[DECISION]` (W₂-only); freeze handoff §2 item 5. Never run. No T-number on file. |

**Consequence for A-001.** A-001 says "T1.28 is the final Phase 1 task". That is false as worded: four Stage 1
tasks followed it, and two of them are parked, not closed. A-001 cannot be confirmed in its present form. §9 states
what can be confirmed instead.

## 7. Supersession boundary delta

The manifest's §5.3 sources are unchanged in location. Both `SUPERSEDED.md` files changed after 2026-06-29:

| Commit | Date | Change |
|---|---|---|
| `a9dcccbf` | 2026-07-14 | Exact-W₂ H₁ headlines adopted as canonical; three conventions locked |
| `ccaf79d5` | 2026-07-15 | P01-A Table 1's H₁ column classified greedy-era and unverifiable |
| `c8c6dd13` | 2026-07-16 | T1.38 phase 1: exact non-overlap H₁ rejects; the adverse fork fired |
| `b8c9793e`, `518da347`, `c4b1897d` | 2026-07-16 to 07-17 | The Table 1 H₁ exact rebuild, its revert, and its restoration (#117) |
| `1af52f6d` | 2026-07-18 | H6: the Markov-2 α=1 cell JSONs committed, with a split verdict (landscape L² citable, W₂ do-not-cite) |

Besides the table above, two do-not-cite boundaries were added in this window: the label and cohort shuffle nulls are
`INVALID-BY-CONSTRUCTION` (2026-07-16 `[NEGATIVE]`), and the Markov-2 α-sweep summary's W₂ is `UNVERIFIABLE`
(T1.38 phase 1). Any successor import must take the supersession records at `3fa437a1`, not at the manifest's
snapshot.

## 8. Stage 2 (Phase 2) delta and the freeze

**The freeze.** The 2026-07-18 `[DECISION]` ("APM prose-production lane FROZEN — transition to ARS", #126 `4b143c92`)
and the CONVENTIONS lock ("APM Prose Production Frozen — ARS Transition", locked 2026-07-17) stop all APM prose
authoring and all new APM compute dispatch. They record "Supersession: none". The freeze suspends the remaining
Stage 2 work. It does not dispose of it.

**A wording difference to record, not resolve.** The CONVENTIONS lock says "The compute lane stays open under its
existing hardened gates". The 2026-07-18 `[DECISION]` says "No further APM compute Tasks are dispatched". The
decision is the later and narrower record; the lock text predates it by a day.

**Stage 2 rows now.** From `.apm/tracker.md` at observation time:

| Task | Tracker state | W0 class | Note |
|---|---|---|---|
| T2.1–T2.6, T2.17, T2.18 | Done | `merged_draft` | Wave-1, unchanged |
| T2.7, T2.8 | Done, merged #81 (`36885054`, 2026-07-12) | `merged_draft` | §6.1 and §6.2 |
| T2.9 | Ready | `deferred` (frozen) | |
| T2.10, T2.11 | Ready | `deferred` (frozen) | |
| T2.12–T2.15 | "Manager-reviewed; drafted — awaiting User per-section review" | `unverified` | Branch `paper/p01b-methods-results` reached main through #109 (`a1b89604`) |
| T2.16, T2.16a | Drafted; T2.16a Done (`6c128f6`), awaiting User review | `unverified` | Same branch |
| T2.17a | Done; "not merged" | `superseded` on main | Its branch `paper/p01a-dedup-rewrite` merged as #106 (`10095d44`) and was reverted by #112 (`f1171fd4`). The content is absent from main; the branch is retained (park set). |
| T2.19 | Waiting: 2.16 | `deferred` (frozen) | |
| T2.20, T2.21 | Ready | `deferred` (frozen) | |
| T2.22 | Waiting: 2.9, 2.19 | `deferred` (frozen) | The v2-completion gate |
| T2.23 | Done, #109 | `merged_draft` | P01-B de-scaffolding |
| T2.24 | "Done … PR #106 merged" | `stale_projection` | #112 reverted #106 in full. The row does not say so. |

**Consequence for A-002.** The Plan's Stage 2 scope is still undecided. It has grown from twenty-two tasks to at least
twenty-six rows (T2.16a, T2.17a, T2.23, T2.24 added). No attributed scope decision accepts, defers, removes or
supersedes the remainder. The freeze is a suspension. W0-D2 asks when this is decided.

## 9. A-001 and A-002: what can be confirmed now

- **A-001, restated for confirmation.** Proposed wording for the confirmer: "Every Stage 1 task on the tracker at
  `3fa437a1` is `authoritative`, `superseded`, `deferred` with a parked record, or `prepared`. T1.41 and the Markov-2
  recompute are the only Stage 1 items carrying open research work. No other Stage 1 computational or assurance
  requirement exists." The author has not checked every Stage 1 row against its evidence; that is the confirmer's
  job, with the independent reviewer.
- **Who confirms.** The manifest names "the current Manager". The APM lane is frozen, and no Manager instance is
  active. W0-D1 asks Stephen to name the confirmer.
- **A-002.** Unchanged in substance from 2026-06-29: the merged material keeps its authority as draft; the remaining
  scope is `decision_required` (§8).

## 10. Legacy-path writes after the freeze

From `git log origin/main` on `papers/P01-A-JRSSA`, `papers/P01-B-JRSSB` and `papers/shared` since 2026-06-29:

- **Before the freeze (2026-07-12 to 07-18):** #81, #106, #109, #112, #116, #118. All are APM-lane PRs.
- **After the freeze:** one commit, #277 (`1dbf6b7b`, 2026-09-10, `[DECISION] SYS: re-enable repo-wide CI`). It
  changed three files under `papers/` as part of a repo-wide Ruff cleanup:
  `papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py`, `papers/shared/scripts/income_vars_check.py` and
  `papers/shared/scripts/read_jbstat_dict.py`. The hunks read for this addendum were formatting and unused-import
  removal. The PR body states the F841 removals were checked to be behaviour-preserving.

This is not a migration, and no ARS writer was involved. It is the only post-freeze write to a legacy paper root, and
it shows that a repo-wide tooling change can reach a `legacy_owned` path. G7-B's path/writer registry should say
whether such changes need a carve-out or an owner note.

## 11. No-migration set: current

The manifest's §10 stands, with these changes:

- **Added:** T1.41 and the Markov-2 recompute (parked for ARS); the freeze handoff's §3 park set (the #106 dedup
  prose on branch `paper/p01a-dedup-rewrite`; WT-3; WT-2; the §6.2/§4.3/§S6 prose directions; the t128 and ARS-scale
  briefs). Handoff 07 counts this set as six items; the handoff lists five bullets. This addendum counts five.
- **Retained branches, at observation time:** `pipe/two-machine-check` (`57684e3d`) is unmerged, and T0.3 is still
  paused on the tracker. `run/stratified-w2-perfamily-fdr`, `run/bhps-markov1-credibility` and
  `paper/p01-stage2-wave1` no longer exist as local branches. `run/w2-gap-closure`, `paper/p01a-dedup-rewrite`,
  `paper/p01b-methods-results` and `pipe/gate-liveness-audit` are ancestors of main.
- **Nothing transferred.** The Gate 6 run (P-058) touched only the SPEC-01 route on its own fresh store. Per P-058
  and the runbook, no legacy task, result, claim or path entered it. The store itself was not read for this addendum.

## 12. Manifest §14 review gate: item-by-item disposition

| §14 item | Status at `3fa437a1` |
|---|---|
| T1.28 is the sole remaining Stage 1 task | **Superseded by events.** T1.28 is done, and T1.38 to T1.41 followed it (§6). Replace with the restated A-001 (§9). |
| T1.6's suspect/anti-conservative result and lock are represented correctly | Holds, with the #79 follow-up added (§6) |
| The grouped Phase 1 inventory does not promote a superseded result | Holds only with §7's supersession changes applied |
| The Wave-1/full-Stage-2 distinction is correct | Holds; the full-Stage-2 side is now §8's table |
| The fourteen unlogged Stage 2 tasks are retained or superseded in the Plan | **Open** (W0-D2) |
| T0.3, T1.28, remaining Stage 2 work and provenance-sensitive files are in the no-migration set | Holds, with §11's additions; T1.28 is now terminal and stays `legacy_owned` |
| The fixture shortlist captures the material failures | Holds, extended by the 2026-07-17 failure inventory (invariants I1a–I11a) |
| No active result, task, branch, worktree, cache or paper claim is transferred prematurely | Holds (§11) |

## 13. Bounded delta set and verdict

**The delta set** is §4 to §12 of this addendum, measured from `33ab053e` to `3fa437a1`, on the legacy surfaces
the manifest's §2.1 scope names. It does not cover Discovery items, P04, or the ARS planning tree.

**The reviewer checks, at minimum:**
1. every commit, blob, size and ancestry claim in §4, §6, §7 and §11 against origin/main;
2. that §6 and §8 cover every Stage 1 and Stage 2 row the tracker holds at `3fa437a1`, with none missing or doubled;
3. that §5's trigger dispositions follow from the evidence cited;
4. that no statement here promotes a superseded or unverified result, or edits a June snapshot;
5. §10's characterization of #277's paper-root hunks, in full;
6. the clash dispositions in §14.

**Verdict:** pending. To be filled in by an independent reviewer in a distinct session, against this file's exact
commit, followed by Stephen's disposition.

## 14. Planning clashes (handoff 14) and stale wording

Each clash is recorded with its disposition. Operative replacement wording for the WP6.7 sentence and 06l lands in
G7-C, not here.

| Clash (handoff 14) | Disposition |
|---|---|
| 1. WP6.7 "Nothing in WP6.7 dispatches while T1.28 or either current paper remains active" (06 plan, WP6.7) vs handoff 07 "stale" vs handoff 08 :171 | **Stale in both limbs.** T1.28 is done (§4). Neither paper is active: both are suspended under the freeze (§8). G7-C replaces the sentence with positive preconditions; handoff 08 is historical by its own header. |
| 2. T1.28 shown as both DONE and active (handoff 07 vs the 06-29 addendum vs 03 A-001) | **Resolved here.** §4 records DONE; the 06-29 text is a dated observation. 03's A-001 status line ("T1.28 is now active") is a `stale_projection`, to be superseded by the register entry that accepts this addendum. |
| 3. W0 first deliverable explicit in handoff 07, absent from WP6.7 (06 plan :197) | **Resolved by D-4 and this file.** G7-C encodes it in 06l and 04-plan §4. |
| 4. T1.28's role: migration-only boundary vs broader hold (03 P-026, 06-29 addendum, 04-plan §2) | **Resolved.** T1.28 was always only a legacy-closeout and migration boundary (P-026). Now that it is terminal, it binds nothing beyond §9's A-001 restatement. |

**Other stale wording found** (for G7-C to carry):
- the tracker's T1.28 row "Open (carried…)" (§4) and T2.24 row (§8) are `stale_projection`s in a frozen record and are
  not edited;
- the CONVENTIONS freeze lock's "compute lane stays open" (§8);
- handoff 07 §3's T1.20 row (§4).

## 15. Owner decisions this addendum asks for

| ID | Decision | Recommendation |
|---|---|---|
| W0-D1 | Who confirms the restated A-001, given that no APM Manager is active under the freeze | **Stephen confirms it himself**, after the independent reviewer has checked §6 against the tracker. A fresh "Manager" instance would only be a nominal authority. |
| W0-D2 | When the Stage 2 scope (the fourteen-plus remaining tasks) is decided | **At 06l Step 3, not now.** Nothing in the documentation track or Gate 7 opening needs it. It binds the first ownership transition that touches a paper. |
| W0-D3 | Accept this addendum's §3 state sequence as the series' current state | **Accept**, on the independent verdict |

## 16. Next currency trigger

A further dated addendum is required when any of these occurs:

- T1.41 or the Markov-2 recompute is dispatched, under any authority;
- a Stage 2 scope decision (W0-D2) is recorded;
- any `papers/P01-*` path, `.apm/` tracked file or `SUPERSEDED.md` changes on main;
- a legacy item is proposed for an ownership transition (06l Step 4 or 5).
