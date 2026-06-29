---
type: proposed_addendum
status: review_pending
proposes_addendum_to: transition/W0-legacy-closeout-transition-manifest-2026-06-28.md
snapshot_referenced: c182e64649ddadd1f0e007d137babf22d38225ac
addendum_observed_at_commit: bcc3c0739e17869315f8744a50eac32e995dda13
observed_date: 2026-06-29
author: Independent adversarial reviewer (read-only observation)
authority: NONE — this is a proposal for the current Manager and Stephen. It does NOT rewrite the 2026-06-28 W0 snapshot and is NOT the post-T1.28 seal addendum that W0 §15 reserves for after T1.28 completion and the Stage-2 scope decision.
---

# PROPOSED W0 Currency Addendum (2026-06-29)

**This is a reviewer proposal, not an accepted W0 revision.** W0 is a commit-anchored
snapshot at `c182e646` (2026-06-28). Per W0 §3 and §15, later APM changes do not
invalidate the snapshot; they require an **addendum**. This document records the live
divergences observed read-only at `bcc3c073` on 2026-06-29 so the Manager/Stephen can
decide whether to fold them into a formal addendum. The 2026-06-28 snapshot is left
unmodified. T1.28 and all no-migration work were observed read-only and not touched.

## Divergences from the 2026-06-28 snapshot

### 1. T1.6 merge anchor moved (premature merge reverted, re-merged via PR #55)

W0 cites `551a9888` as T1.6's merge into `main` (§3 "Remote state"; §5.2/§5.4).

Live commit history after the snapshot:

| Commit | Time (2026-06-28) | Meaning |
|---|---|---|
| `551a9888` | 10:29 | "Merge T1.6 BHPS Markov-1 credibility (verdict=suspect) into main" — **premature** (pre-CodeRabbit) |
| `17ae8c91` | 11:00 | "revert premature T1.6 merge (551a9888) — re-route through CodeRabbit-gated PR" |
| `4a450872` | — | "[RESULT] P01-B: T1.6 BHPS Markov-1 credibility (verdict=suspect) — re-review" |
| `7e798464` | 11:14 | "Merge pull request #55 from stephendor/run/t1-6-rereview" — **canonical T1.6 merge** |

T1.6 remains `authoritative` with verdict `suspect / anti-conservative`; only the merge
anchor changed. Any successor import that records T1.6's merge lineage should reference
`7e798464` (PR #55), not the reverted `551a9888`.

### 2. T1.28 is no longer `prepared` with no active compute

W0 §6.2 recorded: no task log, no producing JSON, no active research compute. Live at
2026-06-29:

- `e7204373` "[EXPLORE] P01: tracker — T1.28 BHPS 'data blocker' verified as extractor bugs; fix-extractor follow-up dispatched";
- `results/panel_methodology/fdr/` now contains `bhps_compute_log_2026-06-28.txt`,
  `bhps_cohort_nssec_log_2026-06-29.txt`, `bhps_gender_usoc_rm_log_2026-06-29.txt`
  (last written 21:06 on 2026-06-29), `subgroup_checkpoints/`, and `run_gender_usoc_rm.ps1`;
- still **absent**: any final `stratified_w2_recompute_<date>.json` /
  `stratified_w2_bh_per_family_<date>.json`, and `.apm/memory/stage-01/task-01-28.log.md`.

Interpretation: T1.28 (or its dispatched extractor-fix follow-up) has been executing
BHPS subgroup work since the snapshot and hit a data blocker (extractor bugs) that was
diagnosed and is being fixed; the producing W2/FDR result JSONs are not yet committed.
**T1.28 remains legacy-owned and was not touched by this review.**

**A-001 consequence.** The A-001 confirmation condition ("no additional Phase 1
computational or assurance task remains open after T1.28 review and closeout") must be
re-confirmed against this live state, including the extractor-fix follow-up, before
Phase 1 closeout is asserted.

### 3. A bus-ownership control was backported to legacy APM

`7c8de855` "[PIPELINE] P00: harden APM bus write ownership" (2026-06-28 22:32) — "Require
matching task and agent ownership before updating non-empty bus slots, and preserve
durable history semantics when clearing messages" — edited both
`.claude/skills/apm-communication/SKILL.md` and `.agents/skills/apm-communication/SKILL.md`.

This postdates the `01-current-system-evidence.md` §4.3/§4.5 snapshot and partially
pre-implements the P-009 / F-001 / F-002 bus-ownership-and-collision control **as skill
prose** (an instruction agents may ignore), not as a mechanical gate. The W6 pre-control
oracle for F-001/F-002 should therefore target pre-`7c8de855` behaviour.

## What is NOT changed

- The 2026-06-28 snapshot text and its determinations are unchanged.
- The Stage-2 scope conflict (14 unlogged Plan tasks; T2.22 gate) remains the open
  `decision_required` that W0 §9 records; this addendum does not resolve it.
- No no-migration item (T1.28, T0.3, retained worktrees, superseded-but-live results,
  caches, restricted data) is migrated, swept, or modified.

## Requested action

The current Manager and Stephen to decide whether to (a) adopt this as a formal dated W0
addendum now, or (b) fold it into the post-T1.28 seal addendum W0 §15 reserves for after
T1.28 completion and the Stage-2 scope decision. Either way, the A-001 confirmation should
be evaluated against the live state above, not the 2026-06-28 snapshot alone.
