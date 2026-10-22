---
document: W0 legacy closeout post-terminal addendum
date: 2026-10-21
revision: 3 (2026-10-22), reconciling the re-review at c7ef464b (revision 2 reconciled the delta review at 73d73357)
baseline_manifest: W0-legacy-closeout-transition-manifest-2026-06-28.md
prior_addendum: W0-legacy-closeout-transition-addendum-2026-06-29.md
observation_commit: 3fa437a1
status: under_review
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
open Gate 7 or authorize any dispatch.

**Revision 2** reconciles the independent delta review
(`reviews/g7a-w0-post-terminal-addendum-delta-review-77388ec9-2026-10-22.md`, verdict REWORK REQUIRED, 0 Blocking,
6 Major, 12 Minor, 5 Info). The finding-by-finding disposition is
`reviews/g7a-w0-post-terminal-addendum-reconciliation-2026-10-22.md`. Revision 1 is commit `77388ec9`.

**Revision 3** reconciles the focused re-review of revision 2
(`reviews/g7a-w0-post-terminal-addendum-re-review-8988f463-2026-10-22.md`, verdict REWORK REQUIRED (narrow), 0
Blocking, 2 Major, 3 Minor, 4 Info). Its dispositions are §5 of the same reconciliation record. Revision 2 is commit
`8988f463`. Stephen authorized a read-only read of the P01-A §4.5 draft (`git show`, no edits) for finding R2; that is
the only draft read in this addendum.

## 2. Observation identity

| Item | Value |
|---|---|
| Observation commit | origin/main `3fa437a1` (#387), committed 2026-10-21T22:42:45+01:00; still origin/main on 2026-10-22 |
| Prior observation | `33ab053e` (2026-06-29), the 2026-06-29 addendum's review commit, an ancestor of `3fa437a1` |
| Method | read-only: `git` ancestry, blob, diff and log queries against origin/main; `gh pr view`; `.apm/tracker.md` (its working copy equals `origin/main:.apm/tracker.md`); `.apm/memory/stage-01/` and `stage-02/` task-log headers; `results/trajectory_tda_integration/stage1/SUPERSEDED.md` and `w2_fallback_audit_2026-07-14.json`; the claim-trace audit and the adversarial mathematical review; the vault Computational-Log; `CONVENTIONS.md` |
| Not read | `papers/P01-A-JRSSA/` and `papers/P01-B-JRSSB/` draft files (out of this track's bounds; their state is taken from the claim-trace audit), except `papers/P01-A-JRSSA/drafts/sections/results-escape-regression-foo.md` at origin/main, read with `git show` under Stephen's 2026-10-22 authorization for finding R2 (§6.1); `.apm/plan.md` (the twenty-two-task count is the manifest's); any ARS store |
| Author | the Gate 7 prep session (06u). The author does not establish its own delta verdict (§14). |

## 3. The W0 series as one state sequence (KAN-20)

The W0 documents carry two different `status` values, `review_pending` (the manifest) and `current_state_addendum`
(the first addendum). The manifest's status is the state of its §14 review gate; the addendum's is a document kind.
This addendum states the series' state, and its own, explicitly.

**The series:**

| State | Entered by | Evidence | Owner |
|---|---|---|---|
| `open_partial` | 2026-06-28 manifest | Manifest §15 outcome "PARTIAL — manifest complete, legacy boundary not sealed"; §14 unchecked | The then-current APM Manager and Stephen |
| `open_partial` (unchanged) | 2026-06-29 addendum | Additive observation; §14 still unchecked | Same |
| `post_terminal_recorded` | Stephen's acceptance of this addendum | The accepted revision; the independent delta verdict (§14); Stephen's disposition | Stephen |
| `sealed` | A later decision, not this addendum | Every manifest §14 item resolved (§13), signed by the signatory W0-D1 names, with the restated A-001 confirmed and the Stage 2 scope decided (W0-D2) | The W0-D1 signatory and Stephen |

**This addendum's own states:**

| State | Entered by | Owner |
|---|---|---|
| `drafted` | Revision 1, commit `77388ec9` | Author session |
| `under_review` | Each revision submitted for independent review (revision 1: review `73d73357`, REWORK REQUIRED; revision 2: focused re-review, pending) | Reviewer session |
| `rework_required` | A review verdict of REWORK REQUIRED; the author reconciles and resubmits | Author session |
| `rejected` | Stephen rejects a revision; the series stays `open_partial` and the June snapshots stand alone | Stephen |
| `accepted` | Stephen accepts an exact revision after a PASS or PASS WITH FINDINGS verdict; the series moves to `post_terminal_recorded` | Stephen |

The manifest's frontmatter `review_gate: current APM Manager and Stephen` and §14 ("the current Manager and Stephen
confirm") name the sealing authority. This addendum does not change it. W0-D1 asks Stephen to name the signatory,
because no APM Manager is active under the freeze, and G7-C carries the resulting amendment to A-001's confirmation
condition and to 06l Step 3 ("The Manager explicitly confirms or rejects A-001") as a register entry.

## 4. T1.28 terminal record (KAN-24)

T1.28 is `authoritative` and terminal, subject to the cross-cutting soundness caveats in §7.

- **Merge:** PR #72, merge `703101de6a9ebbdeb7aa56620b87f61dcbe43ce1` (2026-07-09), an ancestor of `3fa437a1`.
- **Result blobs at `3fa437a1`, unchanged since their producing commit `34dddd37`:**
  - `results/panel_methodology/fdr/stratified_w2_recompute_2026-07-09.json`: blob
    `b1a9dd8510bcfe16cce4c521ca90016dad3d3deb`, 10,485 bytes;
  - `results/panel_methodology/fdr/stratified_w2_bh_per_family_2026-07-09.json`: blob
    `a09de18d9b1719f4732cee3c854dc10f660ff8e8`, 9,444 bytes.
- **Solver era:** the WT-6 audit (`w2_fallback_audit_2026-07-14.json`, `non_compute_classified`) classifies both files
  `IMMUNE (exact era)`.
- **Task log:** `.apm/memory/stage-01/task-01-28.log.md` exists, `status: Success`, `commit: 34dddd3`, PR #72.
- **Headline (tracker row and the 2026-07-09 `[RESULT]`):** USoc 12/12 subgroups reject H₀; BHPS 9/11. The two
  non-rejecting BHPS strata (`nssec/Professional-Managerial`, `cohort/1980s`) are the pre-registered underpowered
  smallest cells. The §6.1 contingency was checked and locked by the Manager the same day.
- **Counting note (audit A32):** BHPS 9/11 counts the W₂-only 1940s cohort (W₂ p_adj 0.016; landscape p 0.148, not
  rejected). Under the dual-metric reading P01-B Table 3 uses, it is 8/11.
- **Caveat (A2, §7):** every T1.28 p-value uses the implemented mean-versus-pairs construction, which the 2026-07-18
  adversarial review says is not the documented test and whose calibration is unestablished. The rejection counts
  stand as recorded results. Their inferential reading waits on the A2 registry decision and the T1.41 calibration.
- **The open item it carried:** "T1.20 BHPS regression may have consumed parental-NSSEC=NaN" was audited and closed
  on 2026-07-11: no v2 exposure, no rerun (Computational-Log 2026-07-11 `[DECISION]`; tracker row T1.20 RESOLVED).
  The T1.28 row's own text still says "Open (carried…)". That line is a `stale_projection` (§15).

The 2026-06-29 addendum's §3 ("T1.28 therefore remains active, incomplete") is superseded as current state by this
section. Its historical observation stands for its date.

## 5. The 2026-06-29 currency triggers

The 2026-06-29 addendum §7 named four triggers for a further addendum. Three have fired:

| Trigger | Fired | Evidence |
|---|---|---|
| T1.28 produces a final artefact or terminal Task log | **Yes**, 2026-07-09 | §4 |
| The Manager changes the Phase 1 scope statement | **Yes**, July 2026 | T1.38, T1.39, T1.40 and T1.41 were added after T1.28. The T1.38 pre-registration is dated 2026-07-15 (`pre_registrations_w2_gap_closure_2026-07-15.json`); the four tracker rows first appear on main in `9ca20884` (2026-07-17). |
| The fourteen unresolved Stage 2 tasks are accepted, deferred, removed or superseded through an attributed scope decision | **No** | The 2026-07-18 freeze blocks them but records "Supersession: none" (§9) |
| An active no-migration item is proposed for ARS adoption | **Yes**, 2026-07-18 | The freeze transfers prose production, and with it the remaining Stage 2 work (a manifest §10.1 no-migration item), to ARS; freeze handoff §3: "§6.2 / §4.3 / §S6 prose directions: deferred to ARS". The same decision parks T1.41 and the Markov-2 recompute "for ARS". |

## 6. Stage 1 (Phase 1) delta

### 6.1 Every manifest §5.2 row, re-derived at `3fa437a1`

Revision 1 said the manifest's §5.2 table "stands" and only added rows. That left classes standing that the delta
window changed. Every row is re-derived here against `SUPERSEDED.md` at `3fa437a1`, claim-trace audit §3.1 to §3.3,
the WT-6 audit JSON and the 2026-07-16 `[DECISION]` (non-overlap outcome fork). "Checked" means the row was compared
with those records. It does not mean every artefact value was re-matched.

| Manifest row | Manifest class | Class at `3fa437a1` | Basis |
|---|---|---|---|
| T1.1 | `authoritative` | `authoritative` (unchanged) | No supersession record names it |
| T1.2 parent, T1.2a–f | `superseded` | `superseded` (unchanged) | `SUPERSEDED.md` "Canonical citable files" |
| T1.2g, T1.7 | `authoritative` | `authoritative`, qualified | Outcome A stands on the exact-era 2026-05-30 arms (`SUPERSEDED.md`, 2026-07-14). The dedup comparison's H₁ W₂ cell and decision counts move to `dedup_amendment_comparison_corrected_2026-07-14.json`. The dedup amendment may not be justified by the H₁ W₂ flip, which was greedy→exact (audit A21, A26). WT-6's cell-level H₁ verdict for the 05-30 arms is `UNRESOLVED`. For the truncate arm, WT-6's era-boundary natural experiment verifies more: its committed H₁ mean (6.6314) matches an exact 12-pair subsample (6.6695), not the greedy one (203.22). The first13 arm rests on the day-level boundary only. |
| T1.2h | `stale_projection` | unchanged | |
| T1.3 | `authoritative` | **H₀ W₂ and landscape L² `authoritative`; H₁ W₂ `unverified`** | Its canonical source is `stratified_markov/stratified_markov1_W2_L5000_frozen_2026-05-29.json` (`SUPERSEDED.md`; audit §3.1). WT-6 classifies the 2026-05-13 battery and the 2026-05-02 stratified file, but not this one. It is dated 2026-05-29, the day WT-6 proved `bhps_length_matched_truncate_frozen_2026-05-29.json` was computed with the greedy solver. Its H₁ W₂ solver identity is therefore not established; its H₁ cells' t-ratios near 1 and large H₁ means point towards greedy without proving it. **Outcome A holds on its H₀ W₂ cells alone:** the file's `per_dataset.*.significant_regimes` equal its H₀-rejecting regimes (USoc R0, R2–R6, 6/7, fraction 0.857; BHPS R0, R2, R4, R5, 4/8, fraction 0.5), and every H₁-rejecting regime also rejects at H₀. The A1–A4 caveats apply. (The tracker's "USoc 5/7, BHPS 8/8" describes the superseded 2026-05-13 battery.) |
| T1.4 | `authoritative` | unchanged | Audit §3.2 lists `intrinsic_dim_2026-05-24.json` |
| T1.5 family | `authoritative` | unchanged | Audit §3.2 lists the `h2_check/` set |
| T1.6 | `authoritative` | unchanged, with the #79 follow-up (§6.2) | |
| T1.8 | `authoritative` | **α=1 landscape L² cells `authoritative`; the W₂ α-stability conclusion `unverified`** | The tracker row bases T1.8 on `markov2_alpha_sweep_summary_2026-06-16.json`, which T1.38 Phase 1 classified UNVERIFIABLE (`w2_gap_closure_phase1_2026-07-16.json`, `phase1.markov2_alpha_sweep`). The α=1 landscape cells are citable (H6, `1af52f6d`). Review finding A1 adds a generator confound to every Markov-2 result (§7). |
| T1.9 | `superseded` | unchanged | |
| T1.9b | `authoritative` | unchanged, qualified | Audit §3.2 lists the spanning inference set. Hole H7: the companion `spanning_AUC_W2_2026-06-09.json` matched W₂ has no explicit solver gate (H₀, so immune in principle). |
| T1.10–T1.20 | `authoritative` | unchanged; one record error found (H10, resolved) | **The T1.20 closure's conclusion stands; its quoted Tier 1 values are stale.** The 2026-07-11 `[DECISION]` traced the §4.5 NS-SEC numbers to `tier1_clustered_firth_2026-05-13.json`, `tier2_glmm_firth_2026-05-14.json` and `tier2_svyglm_headline_2026-06-03.json`, quoting Tier 1 OR 0.8351 (p 0.0008) and 0.8949 (p 0.0466). Audit §3.2 names `tier1_clustered_firth_2026-05-16.json` as canonical and the Tier 1 05-13/05-14 files as not to cite; the Tier 2 05-14 file is canonical (audit A41). The 0.8351/0.8949 values exist only in the 05-13 file. The canonical 05-16 file gives OR 1.0455 (p_firth 0.81056) and 1.2161 (p_firth 0.30726). **The §4.5 draft at origin/main carries the canonical values** (Tier 1 1.0455, p 0.8106; 1.2161, p 0.3073; Tier 2 1.0487/1.2324; headline 1.0954/1.1126), read with `git show` on 2026-10-22. So the draft is right, and the decision's Tier 1 quotation is the stale record. The exposure conclusion holds for the canonical file too: the 05-16 file sources `nssec_proxy` from `pasoc90_cc` falling back to `masoc90_cc` (`xwavedat`), not from `covariate_extractor.py`. See §7 (H10) and §15. |
| T1.21 | `authoritative_supersession` | unchanged | |
| T1.22 | `deferred` | unchanged | |
| T1.23 / T1.23d | `authoritative` | unchanged | Audit §3.2 (`ari_om_gmm_normalised_2026-06-24.json`). The S2 Lean spike (2026-07-21) partly mechanizes the bound; informational. Hole H9 concerns a different ARI (H₀-tree-cut vs GMM). |
| T1.24 / T1.24b | `authoritative` | unchanged | Audit §3.2 (`stability_se_stored_2026-06-22.json`) |
| T1.25 | `authoritative` | unchanged | |
| T1.26 / T1.26b | `authoritative` | **H₁ W₂ non-overlap outcome `superseded`; landscape values `authoritative`** | 2026-07-16 `[DECISION]` "non-overlap H1 claim falsified"; `SUPERSEDED.md` (non-overlap entry): the committed greedy remainder d_perm −2.8545 becomes +7.481 with p 0.000999 under exact W₂. T1.26b's `size_or_fraction_artefact` outcome rests on the greedy value. The L=1882 arm and the 20 subsamples need a production re-run (hole H3). |
| T1.27 | `authoritative` | unchanged | |
| T1.29–T1.32 | `authoritative` | unchanged | No supersession record names them |
| T1.33 | `authoritative` | unchanged | Audit §3.2 (`foo_topology/*2026-06-02.json`) |
| T1.34, T1.34a-redo | `authoritative`, `authoritative_supersession` | unchanged | Audit §3.2 (`tier2_svyglm_headline_2026-06-03.json`) |
| T1.35 | `authoritative` | unchanged | |
| T1.36 | `authoritative` | unchanged | |
| T1.37 | `authoritative` | **H₀ W₂ and landscape L² `authoritative`; H₁ W₂ headline blocks `superseded`; LM-sensitivity H₁ W₂ `unverified`** | `SUPERSEDED.md` 2026-07-14 (`a9dcccbf`): H₁ W₂ moves to `headline_vintage_materiality_corrected_2026-07-14.json` (USoc) and `bhps_headline_frozen_corrected_2026-07-14.json` (BHPS). LM sensitivity H₁ W₂ is SUSPECT-UNVERIFIABLE; its design-choice role stands. Its frozen stratified battery is the T1.3 source above. |

The cross-cutting soundness findings (A1 to A4, §7) apply to every Markov-rung p-value in this table. They change
no class here, because no decision has yet been taken on them. They are recorded so that no row is read as
inferentially settled.

### 6.2 Stage 1 rows added after the manifest

| Task | W0 class now | Evidence |
|---|---|---|
| T1.6 CodeRabbit follow-up | `authoritative` | PR #79, merge `823b40ad` (2026-07-11) |
| T1.20 parental NS-SEC audit | `authoritative` (closed) | Computational-Log 2026-07-11 `[DECISION]`; tracker row T1.20; see the §6.1 note |
| T1.28 | `authoritative` | §4 |
| T1.38 W2 gap closure | `authoritative` | Task log `task-01-38.log.md` `status: Success`. Phase 1 (`c8c6dd13`) and phase 2 (`b8c9793e`) both first reached main through #105 (`305a5516`), which had no CodeRabbit review. #111 (`408f52bb`) reverted both. #117 (`e8890fb7`, 2026-07-17) re-landed them, with two CodeRabbit reviews before its merge. The content on main is #117's. |
| T1.39 blob-hash signature repair | `authoritative` (infrastructure) | Task log `status: Success`; `pipe/gate-liveness-audit` (`f3ccae0b`) is an ancestor of main |
| T1.40 Gate 0 liveness | `unverified` (infrastructure) | Task log `status: Partial`. The tracker row records "GATE 0 CLOSED LIVE" on the Manager's addendum. The log and the row disagree. |
| T1.41 double-null calibration panel | `deferred` (parked for ARS) | Freeze handoff §2 item 4; 2026-07-18 `[DECISION]` ("PARKED FOR ARS (User, 2026-07-18)"). Never run. No task log. Inputs on disk at `scratch/w2_fallback_audit/phase2_checkpoints/2026-07-16/` (20 files, 2026-10-21). Its design must answer A3, and may answer A1 and A2 in the same campaign (§7). |
| Markov-2 α=1 exact-W₂ recompute | `deferred` (parked for ARS) | 2026-07-17 pre-registration; 2026-07-18 H6 `[DECISION]` (W₂-only); freeze handoff §2 item 5. Never run. No T-number. **It must not dispatch on the 2026-07-17 pre-registration as filed**: finding A1 requires an amendment whichever way the fork is decided (06u D-7). |

## 7. Post-terminal soundness and provenance record

Two merged documents changed the legacy research record after T1.28. Neither is a result file, but both govern how
the results may be read.

- **The invariant battery** (`docs/plans/strategy/Theorem-Derived-Invariant-Battery-2026-07-18.md`; #131, merge
  `7cdba0d0`, 2026-07-20). It adds `shared/math_invariants.py`, including the P2 double-null calibration harness.
- **The adversarial mathematical review** (`docs/plans/strategy/P01-Adversarial-Mathematical-Review-2026-07-18.md`;
  #132, merge `0e906ad6`, 2026-07-20; Computational-Log 2026-07-18 `[EXPLORE]`). Its class A findings, by pointer:
  - **A1:** the Markov surrogate generator draws the first state from the pooled initial distribution and, at order
    2, the second token uniformly. P01-B §3.2 declares observed-start conditioning; P01-A §S0 matches the code. The
    order-2 deviation is anti-conservative for the Markov-2 rung. Owner fork: fix the generator and recompute, or
    correct the prose and disclose.
  - **A2:** every production p-value compares the mean of B obs-null distances against individual null-null
    distances (`_battery_core.py`), including T1.28's. P01-B §3.3 documents a leave-one-out ratio test that no code
    implements. It is recomputable from retained per-pair arrays.
  - **A3:** rung 4 and 5 p-values are parametric-bootstrap p-values. The double-null calibration the papers cite as
    their warrant is T1.41, which has never run.
  - **A4:** per-cloud filtration truncation couples the statistic to dispersion.
  - Class B (B1 to B7) and class C (C1 to C3): referee-anticipation and interpretive items, by pointer.
  - Its standing consequence (Computational-Log): "the Gate-7 rewrite must not promote rung-4/5 rejection claims
    until the A1 fork is decided and the double-null calibration runs".

**Claim-trace audit holes** (`P01-Claim-Trace-Audit-2026-07-17.md` §3.3), status at `3fa437a1`:

| Hole | Status | Note |
|---|---|---|
| H1 T1.41 double-null panel | Open | Parked for ARS (§6.2) |
| H2 Markov-2 α=1 certified W₂ cells | Open | Parked; pre-registration needs an A1 amendment (§6.2) |
| H3 non-overlap L=1882 arm and 20 subsamples | Open | Production re-run, or Stephen drops the claims |
| H4 rewritten §6.2/§4.3/§S6 prose | Open | ARS prose lane |
| H5 prose consuming the rebuilt Table 1 H₁ rows | Open | |
| H6 source of the certified Markov-2 landscape values | **Resolved** | #129 (`5795a18b`), 2026-07-18 |
| H7 ungated presumed-immune W₂ files | Open | Includes the Markov-2 summary (§8) and the spanning matched W₂ file (§6.1, T1.9b) |
| H8 P01-A p-value formula prose (A11/A17) | Open | ARS prose lane |
| H9 ARI 0.00004 anchor | Open | Re-derive or drop |
| H10 (added here) §4.5 NS-SEC values: the T1.20 `[DECISION]` vs audit §3.2 | **Resolved 2026-10-22: record error, no draft defect** | Raised by re-review R2. The §4.5 draft carries the canonical 05-16 values; the 2026-07-11 `[DECISION]` quotes the do-not-cite 05-13 Tier 1 values. Corrected by a dated Computational-Log correction entry (2026-10-22), not by editing the decision. A successor must not import Tier 1 values from that decision. |

## 8. Supersession boundary delta

Only `results/trajectory_tda_integration/stage1/SUPERSEDED.md` changed after 2026-06-29. The BHPS pointer file
`results/trajectory_tda_bhps/stage1/SUPERSEDED.md` is unchanged since `a67ca4c7` (2026-06-21).

| Commit | Date | Change |
|---|---|---|
| `a9dcccbf` | 2026-07-14 | Exact-W₂ H₁ headlines adopted as canonical; three conventions locked |
| `ccaf79d5` | 2026-07-15 | P01-A Table 1's H₁ column classified greedy-era and unverifiable |
| `c8c6dd13` | 2026-07-16 | T1.38 phase 1: exact non-overlap H₁ rejects; the adverse fork fired |
| `b8c9793e`, `518da347`, `c4b1897d` | 2026-07-16 to 07-17 | The Table 1 H₁ exact rebuild, its revert, and its restoration (#117) |
| `1af52f6d` | 2026-07-18 | H6: the Markov-2 α=1 cell JSONs committed, with a split verdict (landscape L² citable, W₂ do-not-cite) |

**A boundary that `SUPERSEDED.md` does not hold.** T1.38 Phase 1 classified `markov2_alpha_sweep_summary_2026-06-16.json`
UNVERIFIABLE. That classification is recorded in the T1.38 Phase 1 `[RESULT]` (Computational-Log, 2026-07-16), in
`w2_gap_closure_phase1_2026-07-16.json` and in audit hole H7. It is not in `SUPERSEDED.md`. Line 69 of that file still
reads "exact era, presumed IMMUNE … Confirm by gate before citing", and the same file's H6 entry calls the summary
"solver-uncertifiable". Line 69 is a `stale_projection` of a frozen legacy record and is not edited here.

Because manifest §8.1 makes `SUPERSEDED.md` the import source for supersession events, this is an **import-time
conflict**. G7-B must resolve it by manifest §8.4 source precedence, under which a governing decision plus committed
result evidence outranks a summary line. A successor must not import the line-69 classification.

Also recorded in this window: the label and cohort shuffle nulls are `INVALID-BY-CONSTRUCTION` (2026-07-16
`[NEGATIVE]`), and the T1.3 source's H₁ W₂ solver identity is not established (§6.1).

## 9. Stage 2 (Phase 2) delta and the freeze

**The freeze.** The 2026-07-18 `[DECISION]` ("APM prose-production lane FROZEN — transition to ARS", #126 `4b143c92`)
and the CONVENTIONS lock ("APM Prose Production Frozen — ARS Transition") stop all APM prose authoring and all new APM
compute dispatch. They record "Supersession: none" and carry the 2026-07-16 §6.2 HOLD forward. The freeze blocks the
remaining Stage 2 work. It does not dispose of it.

**A wording difference to record, not resolve.** The CONVENTIONS lock says "The compute lane stays open under its
existing hardened gates". The 2026-07-18 `[DECISION]` says "No further APM compute Tasks are dispatched". The lock's
text was committed in `8b4183ee` (2026-07-18T10:36), seven minutes before `4d5dde97` added the decision's sentence.
The decision is the later and narrower record.

**Stage 2 rows.** From `.apm/tracker.md` and `.apm/memory/stage-02/` at observation time. The class column follows
the manifest's §4 classes. The qualifier column carries the claim-trace audit's verdicts for the files a task
produced; the task-to-file mapping is by section title and was not checked against task logs.

| Task | Tracker state | W0 class | Qualifier |
|---|---|---|---|
| T2.1–T2.6 | Done | `merged_draft` | Subject to the audit's per-file verdicts (below). For §4.5 (T2.4), the NS-SEC values were checked against the canonical files on 2026-10-22 and match (H10, §7). |
| T2.17, T2.18 | Done | `merged_draft` | Subject to the audit's per-file verdicts |
| T2.7 | Done, merged #81 (`36885054`, 2026-07-12), User-approved per section | `merged_draft` | Task log `status: Partial`; the tracker's Done postdates it. Audit §6.1: tables VERIFIED*, one rejection-counting inconsistency with P01-B (A32). |
| T2.8 | Done, merged #81 | `merged_draft`, on **HOLD** | Task log `status: Partial`. §6.2 is on HOLD (2026-07-16 User ruling, carried by the freeze). Audit: A24 falsified core, A21 struck, A19 misdescribed. |
| T2.9, T2.10, T2.11 | Ready | `blocked` | Blocked by the 2026-07-18 freeze `[DECISION]` and by the open Stage 2 scope decision (W0-D2) |
| T2.12–T2.15 | "Manager-reviewed; drafted — awaiting User per-section review" | `unverified` | Content reached main through #109 (`a1b89604`), titled as de-scaffolding (T2.23) but also adding four methods files and `results-4-2-tables.md`. #116 and #118 later edited those files. No Stage 2 task logs exist for T2.12–T2.15; the User review is outstanding. |
| T2.16, T2.16a | Drafted; T2.16a Done (`6c128f6`), awaiting User review | `unverified` | T2.16a log `status: Success`; same branch and caveats as above |
| T2.17a | Done; "not merged" | `superseded` on main | Its branch `paper/p01a-dedup-rewrite` merged as #106 (`10095d44`) and was reverted in full by #112 (`f1171fd4`); the content is absent from main. The branch is retained (park set). |
| T2.19 | Waiting: 2.16 | `blocked` | As T2.9 |
| T2.20, T2.21 | Ready | `blocked` | As T2.9 |
| T2.22 | Waiting: 2.9, 2.19 | `blocked` | As T2.9; the v2-completion gate |
| T2.23 | Done, #109 | `merged_draft` | P01-B de-scaffolding |
| T2.24 | "Done … PR #106 merged" | `superseded` on main | Reached main in the same #106 and was reverted with it by #112. The tracker row's "Done" is a `stale_projection` (§15). |

**Claim-trace audit verdicts that bind the merged drafts** (`P01-Claim-Trace-Audit-2026-07-17.md` Parts 1 and 2;
the governing record for draft content; not re-verified here):
- `results-negative-control-wording.md`: **entire file invalid** (asserts INVALID-BY-CONSTRUCTION p-values as
  negative-control evidence).
- `table1-effects-d_perm-rho-CI.md` and the `table1_effects_2026-05-22` family: **all cells unciteable** (greedy-era,
  pre-frozen sources).
- `results-bhps-robustness.md` (§6.2): A24 falsified, A21 struck, A19 misdescribed; on HOLD.
- `supplement-S6-length-matched-dedup.md`: A26 misdescribed (major), the retired flip mechanism.
- `methods-w2-formal-definition.md` and `supplement-S0-null-specification.md`: A11/A17, a wrong p-value
  denominator against a contract-locked object (hole H8).
- `methods-3-2-ladder-markov.md` (P01-B): two MISDESCRIBED rows in the audit.
- Register: every P01-A file except §S8 carries report-style scaffolding (WRONG-REGISTER rows).

**From the adversarial mathematical review, not the audit:** `methods-3-2-ladder-markov.md` (P01-B §3.2) declares
observed-start conditioning that the generator does not implement (review A1, §7).

**Consequence for A-002.** Merged draft material keeps its draft authority **subject to the 2026-07-17 claim-trace
audit verdicts and the §6.2 HOLD**. The Plan's Stage 2 scope is undecided. Fifteen rows need a disposition: the
twelve of the original fourteen that remain (T2.9 to T2.16, T2.19 to T2.22), plus T2.16a, T2.17a and T2.24. The
tracker holds 26 Stage 2 rows in all.

## 10. A-001 and A-002: what can be confirmed now

**A-001, restated for confirmation.** The manifest's A-001 ("T1.28 is the final Phase 1 task") is false as worded:
four Stage 1 tasks followed it. Proposed wording for the W0-D1 signatory:

> "At `3fa437a1`, these Stage 1 computational or assurance requirements are open:
> 1. T1.41, the double-null calibration panel (parked for ARS);
> 2. the Markov-2 α=1 exact-W₂ recompute (parked for ARS; its 2026-07-17 pre-registration needs an amendment for
>    review finding A1 before dispatch);
> 3. the review's A1 generator fork;
> 4. the review's A2 p-value construction decision and its recomputation from retained per-pair arrays;
> 5. hole H3, the non-overlap L=1882 arm and 20 subsamples (re-run, or drop the claims);
> 6. hole H7, the ungated presumed-immune W₂ files;
> 7. the H₁ W₂ solver identity of the T1.3 source (§6.1);
> 8. the T1.40 log/tracker disagreement (§6.2);
> 9. the review's A4 finding: a pinned-α_max sensitivity triage on one headline cell, before deciding whether the
>    witness-complex grid needs it;
> 10. hole H9: re-derive the ARI 0.00004 anchor with its referent recorded, or drop it;
> 11. T1.8's W₂ α-stability conclusion across α ∈ {0, 0.5, 1, 5}: an exact α-sweep, or drop the claim. Item 2 covers
>     α=1 only, and a gate cannot settle item 6 for the summary because it has no cache;
> 12. the review's class B findings B1 to B7, as one scoped item: the signatory decides which, if any, are Stage 1
>     requirements and records the rest as referee-anticipation work for the ARS prose lane.
>
> No Stage 1 computational or assurance requirement exists other than those listed above."

The signatory confirms that list as complete, after the independent check that W0-D1 names. The author has
re-derived every manifest §5.2 row (§6.1) but has not re-matched every artefact value. Hole H10 (§7) is resolved as
a record error and is not a requirement; the class C findings are interpretive and belong to the prose lane.

**A-002.** As restated in §9.

## 11. Post-freeze writes to legacy surfaces

The freeze PR #126 merged at 2026-07-18T12:19Z (`4b143c92`). After it, on the surfaces the manifest's §8 names:

- **Paper roots** (`papers/P01-A-JRSSA`, `papers/P01-B-JRSSB`, `papers/shared`): one commit, #277 (`1dbf6b7b`,
  2026-09-10, `[DECISION] SYS: re-enable repo-wide CI`), part of a repo-wide Ruff cleanup. It changed
  `papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py`, `papers/shared/scripts/income_vars_check.py` and
  `papers/shared/scripts/read_jbstat_dict.py`: formatting, the removal of unused imports (F401: `numpy`,
  `numpy.typing.NDArray`, `typing.Dict`) and one E741 rename (`l` to `label`). The independent reviewer read the full
  diff and found every hunk behaviour-preserving. Before the freeze, the paper roots were changed by #81, #106, #109,
  #112, #116 and #118, all APM-lane PRs.
- **`.apm/` tracked files:** #368 (`452352ff`, 2026-10-17) appended 26 lines to `.apm/tracker.md`, a Working Note
  recording a worktree sweep during the Gate 6 Phase 5 run. No Task row was edited. (`c99eae26`, which trimmed the
  freeze's own Working Note, is part of #126.)
- **Result roots:**
  - `1af52f6d` (2026-07-18T19:05, after the freeze merge, #129): the H6 cell JSONs and the `SUPERSEDED.md` H6 entry.
    It was an explicit User ruling.
  - `5df0c001` (2026-08-05) rewrote seven legacy result files, including `bhps_nonoverlap_reanalysis_2026-06-09.json`,
    both `01_trajectories.json`, `05_analysis.json` and the three 2026-07-14 corrected files. It is a **direct push to
    main with no PR**: it has one parent (`a426b731`) and reuses #215's merge message, and GitHub associates it with
    no pull request. #215 itself merged as `a426b731` and touched no legacy path. `git diff -w --ignore-cr-at-eol`
    shows no change: the rewrite was line endings only. `3bfb279c` (2026-08-08, "restore accepted WP6.4 provenance
    boundary", in #219, merged as `b132406e`) restored them. At `3fa437a1` each of the seven files has the blob it had
    at `33ab053e` or at its first commit. The net effect is nil.
- **Contracts** (manifest §8.1 names `contracts/**/*.yaml` plus binding tests as legacy research authority):
  - #168 (`f523b1e5`, `b18a5222`; merged 2026-07-26) and #169 (`f5c449ad`, `73d58759`; merged 2026-07-26), the
    WP6.3 work, activated `topology-invariants/null-operation-changes-ph-input.yaml` and
    `stochastic-tests/markov-order-provenance.yaml` (both `pending: true` → active), added
    `stochastic-tests/markov-order-provenance-json-validation.yaml`, and edited
    `stochastic-tests/monte-carlo-permutation-p-value.yaml` and `manifests/research-assurance.yaml`. These change the
    enforcement state of contracts the legacy results are read under. No result changed.
  - `811d5a2b` (2026-08-07), a **direct push with no PR**, rewrote three legacy input-provenance manifests:
    `t128-inputs.yaml`, `t138-w2-gap-closure-inputs.yaml` and `b9-om-gmm-inputs.yaml`. `3bfb279c` (#219) restored
    them: `git diff 4b143c92 origin/main -- contracts/manifests/input-provenance/` is empty. Net nil.
  - #334 (`eba3fe69`, 2026-10-06) added `process-invariants/retired-plan-imperatives-quoted.yaml`, an ARS planning
    contract.

None of these is a migration, and none moved authority. Together they show that repo-wide tooling, ARS-lane changes
and **direct pushes with no PR** (`5df0c001`, `811d5a2b`) can reach `legacy_owned` paths. G7-B's path/writer registry
should say whether such writes need a carve-out, an owner note, or a guard.

## 12. No-migration set: current

The manifest's §10 stands, with these changes:

- **Added:** T1.41 and the Markov-2 recompute (parked for ARS); the freeze handoff's §3 park set (the #106 dedup
  prose on branch `paper/p01a-dedup-rewrite`; WT-3; WT-2; the §6.2/§4.3/§S6 prose directions; the t128 and ARS-scale
  briefs). Handoff 07 counts the park set as six items; the handoff lists five bullets. This addendum counts five.
- **Retained branches, at observation time:**
  - `pipe/two-machine-check` (`57684e3d`) is unmerged, and T0.3 is still paused on the tracker.
  - `run/stratified-w2-perfamily-fdr`, `run/bhps-markov1-credibility` and `paper/p01-stage2-wave1` no longer exist
    as local branches.
  - `run/w2-gap-closure`, `paper/p01a-dedup-rewrite`, `paper/p01b-methods-results` and `pipe/gate-liveness-audit`
    are ancestors of main. Their remote branches are deleted (`[gone]` upstreams). The park-set #106 content is
    recoverable from main's history whatever happens to the local ref.
- **Nothing transferred.** P-058's route package covers only the SPEC-01 route on a fresh store, and names no legacy
  item. The claim that no legacy task, result, claim or path entered the Gate 6 store is inferred from that scope.
  The store was not read.

## 13. Manifest §14 review gate: item-by-item disposition

| §14 item | Status at `3fa437a1` |
|---|---|
| T1.28 is the sole remaining Stage 1 task | **Superseded by events.** T1.28 is done, and T1.38 to T1.41 followed it. Replaced by the enumerated A-001 (§10). |
| T1.6's suspect/anti-conservative result and lock are represented correctly | Holds, with the #79 follow-up (§6.2) |
| The grouped Phase 1 inventory does not promote a superseded result | **Holds only with §6.1 applied.** §6.1 re-derives every row; four rows change class (T1.3, T1.8, T1.26/T1.26b, T1.37). Open until the signatory confirms §6.1. |
| The Wave-1/full-Stage-2 distinction is correct | Holds, with §9's classes and audit qualifiers |
| The fourteen unlogged Stage 2 tasks are retained or superseded in the Plan | **Open** (W0-D2); now fifteen rows (§9) |
| T0.3, T1.28, remaining Stage 2 work and provenance-sensitive files are in the no-migration set | Holds, with §12's additions; T1.28 is terminal and stays `legacy_owned` |
| The fixture shortlist captures the material failures | Holds, extended by the 2026-07-17 failure inventory (invariants I1a–I11a) |
| No active result, task, branch, worktree, cache or paper claim is transferred prematurely | Holds (§11, §12) |

## 14. Bounded delta set, scope and verdict

**The delta set** is §4 to §13, measured from `33ab053e` to `3fa437a1`, on the legacy surfaces the manifest's §2.1
and §8 name: Phase 1 and Phase 2 tasks, result and supersession records, coordination records and the two paper roots.

**Scope deviation (W0-D4).** 06l Step 2's inputs include "the current paper and Discovery boundary". This addendum
covers the paper boundary and does **not** cover the Discovery boundary (the legacy Discovery backlog, active
Discovery items, P04 and WT-2/WT-3 beyond their park-set records). It proposes that the Discovery boundary is
inventoried by G7-B (W9) against W11, where the per-item transition relation lives. That is a deviation from 06l
Step 2, for Stephen's acceptance.

**Verdicts:**
- **Revision 1** (`77388ec9`): REWORK REQUIRED, 0 Blocking, 6 Major, 12 Minor, 5 Info
  (`reviews/g7a-w0-post-terminal-addendum-delta-review-77388ec9-2026-10-22.md`, committed `73d73357`).
- **Revision 2** (`8988f463`): REWORK REQUIRED (narrow), 0 Blocking, 2 Major, 3 Minor, 4 Info; M1, M2, M4, M5, M6
  and all revision 1 minors closed (`reviews/g7a-w0-post-terminal-addendum-re-review-8988f463-2026-10-22.md`,
  committed `c7ef464b`).
- **Revision 3** (this file): pending the narrow re-check the re-review's §7 scopes (§6.1's T1.20 row, §7, §9's §4.5
  qualifier, §10 and §11).

## 15. Planning clashes (handoff 14) and stale wording

Each clash is recorded with its disposition. Operative replacement wording for the WP6.7 sentence and 06l lands in
G7-C, not here.

| Clash (handoff 14) | Disposition |
|---|---|
| 1. WP6.7 "Nothing in WP6.7 dispatches while T1.28 or either current paper remains active" vs handoff 07 "stale" vs handoff 08 :171 | **T1.28 limb: stale** (§4). **"Active" limb: ambiguous under the freeze.** The papers are suspended, not disposed, and remain `legacy_owned` (P-026, P-034), with undisposed Stage 2 scope (§9) and parked prose directions (§12). "Suspended" does not by itself satisfy P-026. G7-C replaces the sentence with positive preconditions; handoff 08 is historical by its own header. |
| 2. T1.28 shown as both DONE and active | **Resolved here.** §4 records DONE; the 2026-06-29 text is a dated observation. 03's A-001 status line ("T1.28 is now active") is a `stale_projection`, superseded as current state on this addendum's acceptance. |
| 3. W0 first deliverable explicit in handoff 07, absent from WP6.7 | **Resolved by D-4 and this file.** G7-C encodes it in 06l and 04-plan §4. |
| 4. T1.28's role: migration-only boundary vs broader hold | T1.28 binds legacy closeout through the acceptance of this addendum and its delta review (P-026), and gates legacy deprecation claims (P-034). After acceptance it binds only through A-001 (§10). |

**Stale projections found** (records in the frozen legacy tree or in accepted documents; none is edited here; G7-C
carries them):

| Record | Stale text | Current state |
|---|---|---|
| Tracker row T1.28 | "Open (carried…)" T1.20 audit | Closed 2026-07-11 (§4) |
| Tracker row T1.38 | "`b8c9793` on `run/w2-gap-closure`, not merged" | On main through #117 (§6.2) |
| Tracker row T1.39 | "not merged" | `ad65f1e` is an ancestor of main |
| Tracker row T1.40 | "GATE 0 CLOSED LIVE" | Task log `status: Partial` (§6.2) |
| Tracker row T1.41 | "Ready" | Parked for ARS (§6.2) |
| Tracker row T2.17a | "not merged" | Merged as #106, then reverted by #112 (§9) |
| Tracker row T2.24 | "Done … PR #106 merged" | Reverted in full by #112 (§9) |
| Task logs T2.7, T2.8 | `status: Partial` | Tracker Done; T2.7 User-approved (§9) |
| `SUPERSEDED.md` line 69 | Markov-2 summary "presumed IMMUNE" | UNVERIFIABLE per T1.38 Phase 1 (§8) |
| 03 A-001 status line | "T1.28 is now active" | T1.28 terminal (§4) |
| 03 A-002 | "fourteen" Stage 2 tasks | Fifteen rows need a disposition (§9) |
| Claim-trace audit §3.3 H6 | "Not locatable on `main`" | Resolved by #129 (§7) |
| Computational-Log 2026-07-11 T1.20 `[DECISION]` | §4.5 Tier 1 NS-SEC OR 0.8351/0.8949 (p 0.0008/0.0466) | Values of the do-not-cite 05-13 file; the canonical 05-16 values, which §4.5 carries, are 1.0455/1.2161 (p 0.81/0.31). Corrected by a dated correction entry, not edited (H10, §7). |
| CONVENTIONS freeze lock | "compute lane stays open" | No further APM compute Tasks (§9) |
| Handoff 07 §3 T1.20 row | "never closed" | Closed 2026-07-11 (§4) |

## 16. Owner decisions this addendum asks for

| ID | Decision | Recommendation |
|---|---|---|
| W0-D1 | **Who signs all eight manifest §14 items, including the restated A-001**, given that no APM Manager is active under the freeze. The resulting change to A-001's confirmation condition and to 06l Step 3 is recorded through G7-C's register entry. | **Stephen signs**, after an independent check that covers §6.1 (every re-derived row), §7 and §10's list, not only §6 against the tracker. A fresh "Manager" instance would be a nominal authority. |
| W0-D2 | When the Stage 2 scope (the fifteen rows in §9) is decided | **At 06l Step 3, not now.** Nothing in the documentation track or Gate 7 opening needs it. It binds the first ownership transition that touches a paper. |
| W0-D3 | Accept §3's state sequences as the series' and this addendum's current states | **Accept**, on the independent verdict |
| W0-D4 | Accept the Discovery-boundary exclusion (§14) as a deviation from 06l Step 2, with the Discovery inventory assigned to G7-B against W11, **on condition that the 06l Step 2 amendment G7-C carries states that no Discovery item may take a Step 3 or later action until G7-B's Discovery inventory is accepted** (re-review §6) | **Accept, with the condition.** The Discovery boundary's transition relation is W11's, which is still `review_pending`. Inventorying it here would duplicate G7-B and anticipate W11. The condition keeps Discovery items from reaching Step 3 with no W0-level closeout record. |

## 17. Next currency trigger

A further dated addendum is required when any of these occurs after `3fa437a1`:

- T1.41 or the Markov-2 recompute is dispatched, under any authority;
- a decision is recorded on review findings A1, A2 or A4, on the B1–B7 scope (§10 item 12), or on holes H3 or H9;
- a Stage 2 scope decision (W0-D2) is recorded;
- any `papers/P01-*` path, `.apm/` tracked file, `SUPERSEDED.md` or legacy result file changes on main (the writes
  already recorded in §11 do not re-trigger);
- a legacy item is proposed for an ownership transition (06l Step 4 or 5).
