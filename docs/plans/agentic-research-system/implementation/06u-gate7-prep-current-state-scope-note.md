# 06u — Gate 7 prep: current-state scope note

**Date:** 2026-10-21
**Status:** proposal for Stephen. It records verified state and asks for decisions. It authorizes no drafting of
W9 or the Gate 7 definition, no dispatch, no compute, no store write and no Jira write.
**Capability status (06s §8):** INTEGRATED. Gate 6 is closed against the accepted 06s contract and its recorded
evidence (P-058, "06s Gate 6 Phase 5 is closed"; #381 `df5ba1ec`; the frozen-checkout replay, #386 `bb9d91d4`).
Gate 7 is not open.
**Trigger:** Stephen started the 06s §7 documentation track on 2026-10-21.
**Handoff:** `handoffs/01M5G6WDA43PAEMZCNG3A8S4R0-gate7-prep-handoff.md`.
**Subject:** branch `claude/gate7-prep-docs-5202cf`, cut from origin/main `3fa437a1` (#387, P-061). The branch
should be renamed to `docs/ars-gate7-prep-scope` before any push, to follow the `docs/<desc>` convention.

## 1. Summary

Four findings change the brief's framing:

1. **"Pilot promotion" is a system stage, not an Assay verdict.** The Gate 7 opening bar in 06l and handoff 07
   ("Gate 6 pilot-promotion evidence") refers to W6's closed `gate_stage: pilot_promotion` and to 04-plan §6's
   "Promotion to broader use" criteria for the pilot. It does not mean a Discovery PROMOTE. The Gate 6 PARK is
   not why the bar is unmet. The bar is unmet because 06s §4 replaced the Gate 6 closure contract and never
   produced `pilot_promotion`-stage evidence. The proposal in §5 replaces the bar with 06s §4 closure evidence
   and moves `pilot_promotion` evidence to a per-item dispatch condition.
2. **P-033 no longer binds.** P-042 (2026-07-26) superseded it (06g §2). Gate 7 compute runs, if at all, under
   P-042's operator-mediated model. Three narrower questions remain, set out in §7.
3. **T1.20 is closed.** The Computational-Log closed it on 2026-07-11 ("no v2 exposure", no rerun), and
   `.apm/tracker.md` marks it RESOLVED. Handoff 07 §3 (2026-07-18) still lists it as unclosed. It leaves the
   manifest as an open item.
4. **Two merged P01 documents are missing from handoff 07's manifest.** These are the adversarial mathematical
   review (#132, merged 2026-07-20) and the theorem-derived invariant battery (#131, merged 2026-07-20). Finding
   A1 of the review means the Markov-2 recompute pre-registration needs an amendment before it can dispatch.

There is also a design gap. 06l Steps 1 to 7 sequence ownership transitions only. Nothing yet says how parked
legacy compute (T1.41, the Markov-2 recompute) is dispatched under ARS while the papers stay `legacy_owned`.
W9 (G7-B) must answer that.

## 2. What was read and how state was verified

- **Authorities read in full or at the named sections:** 06s §§1–4, Phase 4, Phase 5, §§7–11; handoff 07; 06l;
  handoffs 14 and 16; register entries P-026, P-031 to P-034, P-042, P-047, P-050, P-058 (closure, known limits,
  follow-ups), P-060, P-061, A-001, A-002 and the W11 status note; 04-plan (whole); 02-roadmap W9; 00-master §8;
  the runbook §§0–6; 06g §2; 06c gate-stage table; `design/README.md`.
- **Legacy record:** `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md` §3.3; the vault Computational-Log
  (every P01 entry from 2026-07-11 to the newest, 2026-07-21); `.apm/tracker.md` rows T1.20, 1.28, 1.38, 1.41
  (read only); `.apm/memory/handoffs/2026-07-17-apm-freeze-and-ars-transition-instructions.md` §§2–3 (read only).
- **Git:** origin/main `3fa437a1`; `gh pr view` for #118, #126, #129, #131, #132; `git ls-tree origin/main` for the
  result files named below. Branch `docs/ars-gate7-legacy-integration-brief` has no commits beyond origin/main,
  so there are no prior drafts. No `design/09-migration*` file exists in any commit.
- **Filesystem (read only):** T1.41's inputs at `C:\Users\steph\TDL\scratch\w2_fallback_audit\phase2_checkpoints\2026-07-16\`
  hold 20 files.
- **Jira (read only, 2026-10-21):** KAN-12 to KAN-27, KAN-36 to KAN-40, KAN-53, KAN-59 to KAN-61, KAN-64,
  KAN-103. Summaries, status, labels, parent and links were read. Descriptions were not, and 06s §9 requires
  them before any write.
- **Not verified here:** the paper drafts (out of bounds), so each H-hole's draft-level state is carried from the
  2026-07-17 audit and the later log. Line-level re-verification is G7-A's delta review.

## 3. Status of every Gate 7 input

| # | Input | Source pointer | Verified state (2026-10-21) |
|---|---|---|---|
| 1 | Gate 6 closure | P-058 "06s Gate 6 Phase 5 is closed"; #381; #386 | Closed and replayed. KAN-12 and KAN-103 Done. |
| 2 | Gate 7 doc-track authority | 06s §7; handoff 07 (owner-approved 2026-07-18) | Trigger given 2026-10-21. Handoff 07 is partly stale (§9). |
| 3 | Opening bar | 06l §2.2 item 5, §3, Step 1, §6; handoff 07 §1, §5 | Names "Gate 6 pilot-promotion evidence". Not met and not producible under 06s (§5). |
| 4 | SCALE-01 | P-031 (supersession note); P-050; 06l banner; WP6.4 | Not a Gate 6 prerequisite. Package v1.0.3 stays `pending_wp6_6`, `dispatchable: false`. |
| 5 | W6 `pilot_promotion` stage | P-030 stage rule; 06c table; 05-plan S-005, S-007, S-014–S-016; P-029 F-037/F-038 | Defined. Not part of 06s §4, so not exercised by the closure. |
| 6 | W0 post-terminal addendum and delta review | 04-plan §2; P-026; 06l Step 2; KAN-15 | Outstanding. `transition/` holds only the 2026-06-28 manifest and 2026-06-29 addendum. |
| 7 | A-001, A-002, full Stage-2 disposition | 03 register A-001/A-002; 06l Step 3 | Open. A-001's status line still says "T1.28 is now active". |
| 8 | T1.28 | 06l §2.1; PR #72 `703101d` | DONE (2026-07-09). Recorded nowhere in the W0 series yet. |
| 9 | T1.41 double-null panel (H1) | freeze handoff §2 item 4; log 2026-07-16 `[DECISION]` | Parked for ARS, never run. No result on main. Inputs on disk. Pre-reg due at dispatch. |
| 10 | Markov-2 α=1 recompute, W₂-only (H2) | log 2026-07-17 pre-reg; H6 ruling 2026-07-18; freeze handoff §2 item 5 | Parked for ARS, never run. H6 cells on main (#129). Needs a pre-reg amendment for review finding A1. |
| 11 | §3 park set | freeze handoff §3 | Five bullets on file; handoff 07 says six. #106 reverted by #112; branch `paper/p01a-dedup-rewrite` retained. |
| 12 | Audit holes H1–H9 | claim-trace audit §3.3 | H6 resolved (#129). H1, H2, H3, H4, H5, H7, H8, H9 open as of the audit. No later log entry closes them. |
| 13 | T1.20 parental NS-SEC audit | log 2026-07-11 `[DECISION]`; tracker row T1.20 | **Closed**, no exposure, no rerun. |
| 14 | H3 non-overlap arm | audit H3; log 2026-07-16 outcome fork | Open. Needs Stephen's scope decision (re-run or drop the claims). |
| 15 | Failure inventory I1a–I11a | `docs/plans/strategy/APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md` | Current. Binds Gate 7 deliverables. |
| 16 | Adversarial mathematical review | `docs/plans/strategy/P01-Adversarial-Mathematical-Review-2026-07-18.md`; #132 merged 2026-07-20 | **Not in handoff 07.** A1 to A4 open; A1 is an owner fork. |
| 17 | Invariant battery | `docs/plans/strategy/Theorem-Derived-Invariant-Battery-2026-07-18.md`; #131 merged 2026-07-20 | **Not in handoff 07.** Its P2 harness is the proposed calibration route for A1 to A3. |
| 18 | S2 Lean spike (B9 ARI bound) | log 2026-07-21 `[RESULT]` | Partial (T3, T6 proved; T1, T2, T4 `sorry`). Informational for P01-A B9. |
| 19 | SPEC-01 continuation | P-061 | Recorded as "Gate 7+ intake". Not legacy work (§6.2). |
| 20 | P-058 follow-ups | P-058 closure, "Follow-ups" | Public writers for the governing scientific-review record and the verify-restore payload; F7 items at any revisit. No Jira. |
| 21 | P-060 pin split | P-060 | Activatable now that 06s §8 reads INTEGRATED. Not a Gate 7 prerequisite. No Jira. |
| 22 | W11 acceptance | `design/11-…` header; 03 W11 status note; KAN-19 | Document says `review_pending` r0.5 with D-G6-4 limb 1 open. KAN-19 is Done. **Conflict to resolve** before 06l Step 4. |
| 23 | Manuscript-review capability | P-047 point 3 | Gate 9 owns RM-04's manuscript-review pilot and the G-RM-5/G-RM-13 use decision. |
| 24 | Handoff 14 clashes | handoff 14 §§1–4 | Open. Disposition per clash in §9. |
| 25 | Live-run evidence root | P-058 "Where the run's evidence lives" | Owner machine, `C:/Users/steph/.codex/tmp/g6-p5/`, index `66d45785…`. |

## 4. What the Gate 6 record exercised

From P-058 and the runbook §3 status list:

**Live, on `TDL-ARS-G6-Control` (91 events, bound to M2 `4d867d85`):**
- reserve, foundation re-pin, init and first binding (L1 to L7);
- grant activation, `bootstrap_genesis`, `bootstrap_assay_authority` (8 effects by 7 actors);
- Task creation and a running Attempt before `observe_source`;
- `observe_source` (no correction);
- `request_spec_01`, `prepare_spec_01`, the operator return, `return_spec_01_complete`;
- `review_spec_01_complete` with an independent approving outcome review;
- `decide_spec_01`: owner PARK with R1 to R6 and the rule;
- closure: `CompleteAttempt`, `close_task` with an independent Task review, the ProjectUseDecision
  `retain_experimental_benchmark`, independent project-use review, accepted result;
- fresh-process JSON and Markdown result renders;
- governed same-disk backup and an evidence-only `RestoreVerified`;
- independent final evidence review (PASS WITH FINDINGS);
- post-merge replay from the frozen checkout, byte-identical.

**Assembled and tested on scratch only (Phase 4, 4a′ and 4b):**
- the Partial return and review pair, ending `assay_revisit_eligible`;
- revisit from a Partial Assay, `authorize_spec_01_retry` (RETRY), `request_spec_01_retry`, a new Assay;
- PROMOTE and the separately approved SPEC-02 sequence;
- `correct_spec_01_source` (D4 causal-prefix correction);
- wrong-role, missing-approval, concurrent-advance and crash controls.

**Reproduced on scratch and recorded as a known limit:** a scored-Assay PARK cannot be revisited by OR-009, and
the revisit predicate reads one SOURCE observation with a single fact (P-061, carried items).

**Excluded from the run's route package** (`SPEC-GATE6-RUN-V1`, `intentional_exclusions`): OR-008 to OR-011,
cancellation, revisit and retry (P-061).

**Never exercised anywhere:** a KILL outcome live; a PROMOTE live; SPEC-02 live (0/126 + 0/42 under D6); a
second model family in any session; a recorded negative review on the ledger.

**Known limits carried (P-058):** the lapsed and unreleased 1 h lease; the two internal-API seams; Task acceptance
asserting all five criteria; approve-only reviews; the bar review as fixed literals; one model family throughout.

## 5. Opening condition

### 5.1 Finding

Three texts set the bar:

| Source | Bar |
|---|---|
| 06l §2.2 item 5, §3, Step 1, §6 | "exact Gate-6 pilot-promotion evidence" plus Stephen's separate opening decision |
| Handoff 07 §1 item 2 | "Sequenced strictly after Gate 6 pilot promotion evidence exists, so the machinery that receives the papers has been proven on the non-critical SCALE-01 workload first" |
| Handoff 07 §5 item 3 | "until Gate 6's pilot-promotion milestone is recorded and Stephen separately authorizes Gate 7 opening" |
| 06s §7 (latest) | "Gate 7 opening requires Gate 6 closure evidence and separate owner authorization" |

"Pilot promotion" has a precise meaning in the record. P-030 gives W6 sole ownership of the closed `gate_stage`
enumeration, whose last value is `pilot_promotion`. 06c defines it as "Evidence required before pilot
evidence/claims may advance". 04-plan §6 lists the criteria for "Promotion to broader use": deterministic replay
and recovery; no silent overwrite or ambiguous authority; complete provenance; successful required scientific and
operational graders; smaller context without reduced governing-evidence recall; acceptable operator burden; and
Stephen's approval for any R3 or claim transition.

So the bar was never "SPEC-01 must PROMOTE". Stephen's reading ("we have run the system up to the
promotion/park/kill point") is right that the Assay verdict point was reached. It does not by itself meet the
written bar, because the written bar names a stage the 06s contract dropped.

Measured against 04-plan §6, the Gate 6 record:
- **meets:** deterministic replay and recovery (steps 5 and 6); no silent overwrite (append-only ledger, replay
  through the tail); provenance (hash-pinned scripts, the evidence index); Stephen's approval at every owner
  point;
- **partly meets:** "required scientific and operational graders". Independent reviews approved, but they were
  approve-only, one model family, and D-G5-1(a) still blocks M/H graders;
- **does not address:** "smaller context without reduced governing-evidence recall" and "acceptable operator
  burden". Neither was measured. The live steps ran from 2026-10-16 to 2026-10-21 as separately authorized
  batches.

### 5.2 Proposal (old → new, for a new register entry; nothing is edited in place)

**06l §2.2 item 5, §3 "Gate-7 opening/dispatch bar", Step 1 inputs/proof, Step 4 inputs and §6:**

> *Old:* "exact Gate-6 pilot-promotion evidence" (and "Gate-6 pilot-promotion evidence").
>
> *New:* "Gate 6 closure evidence under the accepted 06s §4 contract: P-058's recorded closure, the docs-only final
> PR #381 (`df5ba1ec`) and the post-merge frozen-checkout replay (#386, `bb9d91d4`)."

**Handoff 07 §1 item 2:**

> *Old:* "Sequenced strictly after Gate 6 pilot promotion evidence exists, so the machinery that receives the
> papers has been proven on the non-critical SCALE-01 workload first (preserving the intent of P-031)."
>
> *New:* "Sequenced strictly after Gate 6 closure under 06s §4 (P-058), whose fresh bounded run proved the
> receiving route on a non-critical workload: SPEC-01, which ended in an accepted `retain_experimental_benchmark`
> result with no scientific claim. This preserves P-031's intent. SCALE-01 is not a condition."

**Handoff 07 §5 item 3:**

> *Old:* "Nothing dispatches from the accepted documents until Gate 6's pilot-promotion milestone is recorded and
> Stephen separately authorizes Gate 7 opening."
>
> *New:* "Nothing dispatches from the accepted documents until Stephen separately authorizes Gate 7 opening.
> Gate 6 closure evidence (P-058, #381, #386) is on file."

**New per-item condition, carried in the Gate 7 definition (G7-C):**

> "A Gate 7 item that would accept research evidence, change a result's citability or advance a claim dispatches
> only after the W6 `gate_stage: pilot_promotion` evidence that applies to it is produced or explicitly waived by
> Stephen, with its fixture IDs named (S-005, S-007, S-014 to S-016, F-037, F-038 as applicable)."

**Rationale.**
- The 06s §4 contract is the accepted Gate 6 bar, and 06s §4 itself says later gates "cannot add closure
  prerequisites". An opening bar that names a stage 06s dropped can never be met, so it is a dead condition,
  not a safeguard.
- What `pilot_promotion` protects, the advance of evidence and claims, does not happen at opening. Opening
  authorizes intake documents and bounded dispatch. Binding the stage to the items that advance claims keeps
  the protection where the risk is.
- 04-plan §6's unmeasured criteria (context recall, operator burden) become explicit Gate 7 questions instead
  of silent assumptions.

### 5.3 SCALE-01: drop it as an opening condition

**Recommendation: drop it.** Leave the package as historical evidence. Do not run it for Gate 7.

- P-050 and 06l's banner already removed SCALE-01 from Gate 6. Only handoff 07's wording still ties it to Gate 7.
- P-031's intent was to prove the machinery on a non-critical workload before the papers. The fresh SPEC-01 run
  did that, from genesis to replay, on a workload whose accepted outcome makes no claim.
- SCALE-01 would exercise a different workload class (stage telemetry and Markov-fit hoisting on closed fixtures).
  It would not exercise the branches Gate 7 actually lacks: PROMOTE, revisit, retry and SPEC-02 (§4), or a second
  model family.
- Running it is not free. WP6.4 required its briefs to be re-hashed against the real ScopeDefinition schema
  before dispatch, and the package predates the 06s route.

**What would add evidence, if Stephen wants more before opening:** a live exercise of revisit/retry, which the
SPEC-01 continuation (P-061) will provide anyway at its own gate. That is a reason to keep the continuation on
the record, not to run SCALE-01.

## 6. Refreshed intake manifest (replaces handoff 07 §3 by pointer)

### 6.1 Legacy research items (P01-A and P01-B, `legacy_owned`)

| Item | State | Pointer | Dispatch precondition |
|---|---|---|---|
| W0 post-terminal addendum and bounded delta review | Outstanding | 04-plan §2; P-026; 06l Step 2; KAN-15 | None for authoring (G7-A) |
| T1.41 double-null calibration panel (H1) | Parked for ARS; inputs on disk (20 files), regenerable from `scratch/w2_fallback_audit/w2_gap_closure_table1_h1.py` | freeze handoff §2 item 4; log 2026-07-16 `[DECISION]` | Pre-reg at dispatch; scope per review A3 (one campaign may answer A1 to A3); the §7 questions |
| Markov-2 α=1 exact recompute, W₂-only (H2) | Parked for ARS; ~8.7 h/cell full regeneration; L² side certified from the #129 cells | log 2026-07-17 pre-reg; 2026-07-18 H6 `[DECISION]`; freeze handoff §2 item 5 | **Pre-reg amendment for review A1** (the generator's uniform second token at order 2) before dispatch; Stephen's A1 fork |
| §3 park set | #106 dedup prose (branch retained, revert #112); WT-3; WT-2; §6.2/§4.3/§S6 prose directions; t128 and ARS-scale briefs | freeze handoff §3 | G7-A reconciles the count (five bullets vs "6 items") |
| Audit holes H1–H5, H7–H9 | Open (H6 resolved by #129) | claim-trace audit §3.3 | Per hole; H4 and H8 are prose |
| H3 non-overlap L=1882 arm + 20 subsamples | Open | audit H3; log 2026-07-16 outcome fork | Stephen's scope decision: re-run or drop the claims |
| Adversarial mathematical review A1–A4, B1–B7, C1–C3 | Open; A1 is an owner fork | `docs/plans/strategy/P01-Adversarial-Mathematical-Review-2026-07-18.md`; #132 | No rung-4/5 rejection claim advances before A1 is decided and the calibration runs (log 2026-07-18) |
| A-001, A-002, full Stage-2 disposition | Open | 03 register; W0 addendum 2026-06-29; 06l Step 3 | Binds affected transitions only |
| T1.20 parental NS-SEC audit | **Closed 2026-07-11** | log 2026-07-11; tracker row T1.20 | None. Carried as a closed record. |
| Result-bearing #105 merged without CodeRabbit review | Content on main (`w2_gap_closure_table1_h1_2026-07-16.json`) | tracker 2026-07-17 note | G7-A delta review records the gate gap |

### 6.2 ARS-native continuation (not legacy; P-061 calls it "Gate 7+ intake")

- **Route:** a new route-package version admitting OR-009, OR-010 and OR-011, with its own authority review and
  closed-input discipline (P-061 point 2).
- **Retry identity:** a retry Assay with its own Task and Attempt. This differs from P-058 4b-1's one-Task-lineage
  rule, and the route-package review settles the difference (P-061, carried items).
- **Revisit predicate:** the scored-Assay PARK revisit limit and the single-fact predicate (P-061, carried items).
- **SPEC-02 v1.2.0 plus R6:** review, contract version, the connected-components amendment, and the route
  package's source-binding update. The draft (`spec-02-amendment-draft-v1.2.0.md`, `de29763b…`) is outside the
  repository (P-061 point 5).
- **R4 crosswalk task:** documentation only, `/bhps-wave-crosswalk`, no microdata. Authorized only when the later
  gate opens (P-061 point 6).
- **R5 threshold pre-registration:** in the vault, before any survey PH (P-061 point 7).
- **Binding decisions:** OD-1 to OD-8 (P-061 point 3). OD-7's venv (CPython 3.10.4, numpy 1.23.5, scipy 1.10.0)
  is not installed and is a retry prerequisite.
- **F7 items:** dtype and tolerance binding; unversioned diffusion figures (P-058 follow-ups).

### 6.3 Gate 6 follow-ups that a later live run will hit

- A public writer for the governing scientific-review record (P-058). Any later project-use acceptance,
  including the SPEC-01 continuation's, needs either this writer or another option-A owner placement.
- A public deriver for the verify-restore payload (P-058).

### 6.4 Standalone, not Gate 7

- **P-060, the 06t pin split.** Activatable now: 06s §8 reads INTEGRATED. It is a standalone job for Stephen to
  dispatch, with the uniqueness invariant and its negative control as its binding. It must land before any
  acceptance of the 06i candidate.

### 6.5 Enforcement inputs (bind every Gate 7 deliverable)

- Failure inventory → invariants I1a–I11a.
- The invariant battery (#131), including the P2 calibration harness.
- No self-attestation; review by a distinct agent session; Stephen's exact-revision acceptance.

## 7. The P-033 question

**P-033 does not bind Gate 7.** P-042 (2026-07-26) "Supersedes: P-033 and the active first-release sequence in
P-035". 06g §2 records P-033 as superseded: live transports, parity, live-grader activation and evaluated profiles
"are not first-release prerequisites". Gate 6 ran its research Assay under P-042's operator-mediated model.

Three questions remain. They are surfaced here, not resolved:

1. **Is Gate 7 still "first release"?** P-042 removes the live-provider programme "from the first-release scope"
   and says reactivation "requires a new owner decision". If Gate 7 is inside the first release, legacy compute
   dispatches operator-mediated, as Gate 6 did. If it is not, Gate 7 must say what replaces P-033.
2. **Review independence for claim-bearing compute.** D-G5-1(a) still blocks M/H model-graded acceptance. Gate 6's
   reviews all ran on one model family (a P-058 known limit). T1.41 and the Markov-2 recompute feed paper claims.
   P-005 reserves claim promotion and R3 dispatch for Stephen, and P-029 blocks R3 dispatch when fewer than two
   eligible model families cover the required capability (`r3_family_coverage_insufficient`). Two things are not
   stated anywhere: the risk tier of these compute items, and whether P-029's family rule binds
   operator-mediated sessions under P-042.
3. **How legacy compute runs at all.** P-026 forbids ARS from writing legacy-owned tasks, evidence or claims, and
   06l sequences only ownership transitions. For T1.41 to run under ARS, either the item transitions first
   (06l Step 5), or ARS produces a new successor-owned result that a legacy-owned paper later cites. W9 must
   choose, because 06l does not.

**Sequencing consequence:** none of the three blocks the documentation track or opening. All three block the first
compute dispatch. G7-B and G7-C should carry them as explicit owner decision points.

## 8. Proposed scope and order

### 8.1 Documents (06l Step 0)

1. **G7-A: W0 post-terminal addendum and bounded delta review** (KAN-15, with KAN-23, KAN-24, KAN-20).
   - A new dated file under `transition/`. It records T1.28 DONE with its merge and blob identities (06l §2.1),
     preserves the June snapshots, lists every post-terminal divergence, and records T1.20's closure.
   - Reconciles handoff 14's four clashes and the stale wording in §9, as old→new text.
   - Its delta set includes the §6.1 items, the merged-without-review #105 and the park-set count.
   - An independent reviewer returns the delta verdict.
   - **Timing clash:** 06s §7 puts this in the documentation track; 06l Step 2 places it after opening. 06l also
     says it is "not an opening prerequisite". Proposed: author and review it now under 06s, and amend 06l Step 2
     to "accepted before any Step 3 or later action". Decision D-4 below.
2. **G7-B: W9** (KAN-13), at `design/09-migration-compatibility-and-pilot.md` (decision D-5).
   - Everything handoff 07 §1 item 1 and 02-roadmap W9 require.
   - Plus: how parked legacy compute is dispatched (§7 question 3); the per-item `pilot_promotion` condition (§5.2);
     the path/writer registry and boundary matrix (KAN-26); and how 04-plan §6's unmeasured criteria are measured.
   - Depends on G7-A's delta verdict for the legacy inventory.
3. **G7-C: the Gate 7 definition in 04-plan §4** (KAN-14, with KAN-16, KAN-17, KAN-25).
   - Gate 7 section, currency note, intake manifest by pointer to §6 of this note (or its accepted successor).
   - Old→new wording for P-026, P-034, WP6.7 and the opening bar (§5.2), proposed as one new register entry.
   - A Gate 7 capability-reporting table, modelled on 06s §8.

Each document: independent adversarial review by a distinct session (`adversarial-design-review`), then
reconciliation, then Stephen's acceptance of the exact revision. Order A → B → C. B and C could overlap once A's
delta verdict is in, but C cites B, so C is accepted last.

### 8.2 Later 06l steps (not authorized by anything here)

| Step | Content after these proposals | Still needs |
|---|---|---|
| 1 Open Gate 7 | Accepted G7-A to G7-C; 06s §4 closure evidence; Stephen's opening decision | KAN-22 to KAN-26 contradictions closed |
| 2 W0 addendum | Already accepted in G7-A if D-4 is taken; Step 2 becomes a check | — |
| 3 A-001, A-002, Stage-2 | Attributed disposition manifest | The current Manager's A-001 confirmation; Stephen's scope rulings |
| 4 First transition inventory | Proposed first batch | **Accepted W11** (D-G6-4 limb 1; the KAN-19 conflict in §3 row 22); path/writer registry |
| 5 Per-item transition | One item at a time | The §7 answers for any compute-bearing item |
| 6 Whole-path cutover | One path | All its items transitioned |
| 7 Retirement | One surface | Durable cutover |

Compute items (T1.41, Markov-2) and the SPEC-01 continuation sit outside 06l's steps. G7-C places them.

## 9. Stale wording and clash register

| Location | Text | Disposition |
|---|---|---|
| `06-wp6-gate6-readiness-and-integration-plan.md` WP6.7 | "Nothing in WP6.7 dispatches while T1.28 or either current paper remains active" | Stale: T1.28 DONE; both papers suspended (#126). Replace with positive preconditions (G7-C). Handoff 14 clash 1. |
| `08-wp6-context-budgeted-manager-handoff-prompt.md` :171 | "while its W9/T1.28/current-paper gates remain" | Same. |
| W0 addendum 2026-06-29; 03 A-001 status line | T1.28 "active" | Historical snapshots. G7-A records DONE in a new addendum; neither is edited. Handoff 14 clashes 2 and 4. |
| 06-wp6 plan :197 vs handoff 07 §1 | W0 first deliverable not encoded in WP6.7 | Handoff 14 clash 3. G7-C encodes it (KAN-25). |
| 06l banner and 03 "Gate 6 reset note (2026-08-22)" | "governed only by 06q" | 06s superseded 06q (06s header). Note in G7-C. |
| 06l §2.2, §3, Step 1, Step 4, §6 | "pilot-promotion evidence" | §5.2. |
| 06l §2.3 Jira table (2026-08-01) | KAN-12, KAN-61 open | Stale (both Done). |
| Handoff 07 §1 item 2, §5 item 3 | Pilot-promotion bar; SCALE-01 first | §5.2. |
| Handoff 07 §2 item 4 | "WP6 first wave in flight" | Historical. |
| Handoff 07 §3 T1.20 row | "never closed" | Closed 2026-07-11. |
| Handoff 07 §4 | Gate 7 "consumes Gate 6's outputs (a promoted, proven runtime)" | Read "the closed 06s route". |
| Handoff 07 §4 | "No model-graded acceptance before WP6.2 T1b clears (D-G5-1(a)/D-G6-2)" | P-042 retired D-G6-2 and deferred T1b. Read "while D-G5-1(a) stands". |
| `design/README.md` W9 | `09-migration-compatibility-and-pilot.md`; 06s and handoff 07 say `09-migration-and-pilot.md`; `design/09-wp6-2-t2-…` already uses prefix 09 | D-5. |
| 06s §7 heading | "documentation only, deferred" | Trigger fired 2026-10-21. |
| KAN-22, KAN-60 labels | `blocked-by-gate6` | Gate 6 closed. Jira plan. |

## 10. Proposed Jira plan (no write until Stephen approves; descriptions read first per 06s §9)

| Issue | Now | Proposed change |
|---|---|---|
| KAN-22 Gate 7–9 readiness (parent) | To Do; `blocked-by-gate6` | Remove `blocked-by-gate6`. Description: Gate 6 closed (P-058), doc track triggered 2026-10-21, pointer to this note. In Progress when G7-A drafting starts. |
| KAN-15 W0 addendum and delta review | To Do | Home of **G7-A**. In Progress at drafting. |
| KAN-23 WP6.7 hold language | To Do | G7-A sub-scope (old→new text); closes on G7-A acceptance. |
| KAN-24 T1.28 DONE and W0 state | To Do | G7-A sub-scope. |
| KAN-20 mark W0 manifests coherent | To Do | G7-A sub-scope. |
| KAN-13 W9 | To Do | Home of **G7-B**. Record the filename decision (D-5). |
| KAN-26 boundary matrix | To Do | G7-B sub-scope (path/writer registry). |
| KAN-14 Gate 7 section in 04-plan | To Do | Home of **G7-C**. |
| KAN-16 WP6.7 sequencing addendum | To Do | G7-C sub-scope (old→new WP6.7 and 06l wording). |
| KAN-17 bind four strategy documents | To Do | G7-C manifest. The four are the claim-trace audit, the failure inventory, the invariant battery and the adversarial review (to confirm from its description). |
| KAN-25 first-deliverable precondition | To Do | G7-C sub-scope. |
| KAN-18 W10 roadmap gap | To Do | Unchanged; outside this track. |
| KAN-21 Gate 9 planning sweep | To Do; blocked by KAN-13 to KAN-20 | Unchanged; runs after G7-A to G7-C. |
| KAN-60 WP6.7 aggregate | To Do; `blocked-by-gate6`; blocked by KAN-12 (Done) | Remove `blocked-by-gate6`; keep To Do; links stay. |

**New issues, only on Stephen's word:**
- **SPEC-01 continuation intake** (P-061 says "No Jira issue yet"). Under KAN-22 if D-3 keeps it in Gate 7's manifest.
- **P-060 pin split.** Standalone, created when Stephen dispatches it.
- **P-058 public writers** (scientific-review record, verify-restore payload). One standalone issue. KAN-12 is Done,
  so it has no natural parent.

## 11. Owner decisions needed

| ID | Decision | Recommendation |
|---|---|---|
| D-1 | Replace the "pilot-promotion evidence" opening bar with 06s §4 closure evidence, and carry W6 `pilot_promotion` as a per-item dispatch condition (§5.2 wording) | **Accept**, recorded as one new register entry with G7-C |
| D-2 | SCALE-01 | **Drop it as a Gate 7 condition**; keep the package as historical evidence (§5.3) |
| D-3 | Where the SPEC-01 continuation lives: in Gate 7's manifest as a separate ARS-native section, or in its own later gate | **In Gate 7's manifest by pointer, sequenced independently** of the legacy items, so P-061's "Gate 7+ intake" has one home. Its dispatch bar stays its own. |
| D-4 | Author the W0 addendum now (06s §7) and amend 06l Step 2 to "accepted before any Step 3 or later action" | **Accept** |
| D-5 | W9 filename | **`design/09-migration-compatibility-and-pilot.md`** (the README's reserved name, matching KAN-13), with a README note on the shared 09 prefix |
| D-6 | The §7 questions (first-release scope; R3 two-family rule under P-042; how legacy compute runs) | **Defer to G7-B and G7-C** as named decision points; do not decide now |
| D-7 | Review finding A1's fork (fix the generator and recompute, or correct the prose and disclose) | **Defer to Gate 7 intake**, but record now that the Markov-2 pre-reg needs an amendment either way, so nothing dispatches on the 2026-07-17 pre-reg as filed |
| D-8 | H3 scope (re-run or drop the claims) | **Defer to intake**; no new information since 2026-07-16 |
| D-9 | Manuscript prose under ARS: Gate 7, or wait for Gate 9's manuscript-review capability (P-047) | **G7-C names the dependency**; prose items (H4, H8, the park-set prose) wait on it |
| D-10 | The W11 status conflict (document `review_pending`, KAN-19 Done) | **Verify before G7-B**: read KAN-19's description and the W11 review record; it gates 06l Step 4 only |
| D-11 | The Jira plan in §10 | **Approve**, then the changes are made with read-back |
| D-12 | P-060 | Stephen's call when to dispatch; not Gate 7 work |

Until Stephen decides D-1 to D-5 and D-11, the track drafts nothing further.
