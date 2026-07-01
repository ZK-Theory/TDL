---
deliverable: W0
title: Legacy closeout and transition manifest
snapshot_time: 2026-06-28T10:33:24+01:00
snapshot_commit: c182e64649ddadd1f0e007d137babf22d38225ac
status: review_pending
review_gate: current APM Manager and Stephen
successor: Agentic Research System
---

# W0 — Legacy Closeout and Transition Manifest

## 1. Determination

The repository is at a suitable **transition-design window**, but not yet at a sealed legacy boundary.

At the snapshot commit:

- T1.6 has been independently reviewed by the current Manager, merged into local `main`, and classified `suspect / anti-conservative` under its pre-registered rule;
- T1.28 is the **only open Stage 1 task**, is prepared and queued, and has not begun execution;
- no T1.28 task log, binding test, or producing result JSON exists;
- no research computation process is active on the machine—the observed Python processes are vault and Zotero MCP services;
- eight Stage 2 prose tasks are merged to `main`;
- the full Plan-defined Stage 2 is **not complete**: fourteen of its twenty-two tasks have no Stage 2 task log, including T2.22, which the Plan defines as the v2-completion gate;
- T0.3 remains paused pending a second-machine canary;
- Stages 3 and 4 have not begun.

Consequently:

1. **Phase 1 closeout is pending T1.28.** The current Manager's statement that T1.28 is the only remaining Stage 1 task is accepted as the live coordination state.
2. **Wave-1 Stage 2 prose is complete and authoritative as merged draft material.** The broader statement “Stage 2 complete” is not accepted as full Plan completion without an explicit Plan-supersession decision.
3. **The successor system may be designed now.** It must not take operational ownership of T1.28, T0.3, the remaining Stage 2 work, or later APM stages.
4. **This manifest remains `review_pending`.** It becomes the sealed transition boundary only after the review gate in §14 is accepted.

## 2. Scope and method

### 2.1 Scope

W0 establishes:

- Phase 1 task authority and closeout state;
- T1.28's exact readiness and non-execution state;
- Phase 2 authoritative, provisional, blocked, and missing-work classifications;
- the legacy source hierarchy;
- unresolved tasks and decisions;
- the no-migration set;
- historical failures to preserve as successor-system eval fixtures.

W0 does not:

- execute or dispatch T1.28;
- amend a pre-registration;
- reinterpret a computational result;
- rewrite the APM Plan, Tracker, bus, task logs, or vault;
- sweep a worktree or branch;
- push or commit the transition documents;
- declare the papers submission-ready;
- convert historical Tracker prose into synthetic events.

### 2.2 Assurance lanes

| Lane | W0 treatment |
|---|---|
| Topology | No new topological judgment; preserve locked results and supersession lineage |
| Stochastic / null | Record T1.6 and T1.28 governing designs without changing them |
| Statistical / panel | Preserve FDR, estimand, and ARI decision authority from committed artefacts |
| Representation | Preserve frozen-loadings and data-vintage boundaries |
| Output / provenance | Primary W0 lane: verify paths, commits, manifests, branches, worktrees, and status conflicts |
| Paper claim | Distinguish merged draft prose from final claim promotion and v2 completion |

### 2.3 Evidence procedure

The audit used direct file and Git inspection:

- commit ancestry and worktree state;
- current `.apm/spec.md`, `.apm/plan.md`, `.apm/tracker.md`, task logs, memory index, and bus files;
- committed result JSONs, contracts, pre-registrations, provenance manifests, and supersession manifests;
- paper section files and project status documents;
- the external Computational Log for decision provenance;
- running-process command lines to distinguish research compute from MCP services.

The existing Graphify index was queried first as required. It returned Phase 6 numerical-code nodes and no closeout-control documents. It was therefore treated as non-authoritative for W0; direct repository files supplied the evidence.

## 3. Snapshot identity

| Item | Snapshot value |
|---|---|
| Repository | `C:\Users\steph\TDL` |
| Branch | `main` |
| Commit | `c182e64649ddadd1f0e007d137babf22d38225ac` |
| Commit meaning | T1.6 reviewed and merged; T1.28 now deliverable |
| Remote state | Local T1.6 merge recorded as unpushed in the Tracker |
| Working tree | Pre-existing user changes plus the uncommitted Agentic Research System planning workspace |
| Active research compute | None observed at snapshot |
| Active control services | Vault MCP and Zotero MCP Python processes |

This is a commit-anchored snapshot. Later APM changes do not invalidate it; they require an addendum or a new manifest revision.

## 4. Authority classifications

W0 uses these classes:

| Class | Meaning |
|---|---|
| `authoritative` | Accepted result, decision, or prose artefact supported by committed evidence and current review state |
| `authoritative_supersession` | The record that declares an earlier artefact non-citable and identifies its replacement |
| `merged_draft` | Accepted and merged manuscript material, but not final integrated/humanized submission text |
| `prepared` | Inputs, task envelope, contracts, worktree, and readiness exist; producing work has not begun |
| `active` | Execution or review remains in flight |
| `blocked` | A named external input or decision prevents progress |
| `deferred` | Explicitly removed from the current paper scope or moved to later work |
| `superseded` | Preserved for provenance but not current authority |
| `stale_projection` | A Tracker, task log, report, or project page no longer matches stronger evidence |
| `unverified` | The artefact exists but lacks the required acceptance evidence |

The successor must import the class and source link. It must not infer authority from file presence alone.

## 5. Phase 1 closeout inventory

### 5.1 Current boundary

The current Manager records T1.28 as the only open Stage 1 task. W0 accepts that coordination statement because the remaining task inventory is consistent with it after supersession and deferral are applied.

### 5.2 Task-group classification

| Task or group | W0 class | Authority and treatment |
|---|---|---|
| T1.1 | `authoritative` | Pre-registration entries filed; retained as Stage 1 foundation |
| T1.2 parent and T1.2a–f | `superseded` | Bug-era/per-call-PCA headline values are non-citable; use T1.36/T1.37 frozen reruns and the supersession manifest |
| T1.2g, T1.7 | `authoritative` | Frozen external-indexing-dedup reruns support Outcome A; canonical 2026-05-30/31 artefacts and decision |
| T1.2h | `stale_projection` | The earlier B/C ambiguity was superseded by the later frozen/dedup Outcome A decision |
| T1.3 | `authoritative` | Outcome A survives under the frozen T1.37 pipeline; cite the frozen stratified result, not the pre-frozen battery |
| T1.4 | `authoritative` | Intrinsic-dimensionality result merged and used in accepted prose |
| T1.5 family | `authoritative` | H2 restriction-stands result and corrected-grid confirmation merged; downstream corrections preserved original upstream design boundaries |
| T1.6 | `authoritative` | Manager-reviewed `suspect / anti-conservative`; merged by `551a9888`, Tracker closeout `c182e646`; result JSONs and contracts on `main` |
| T1.8 | `authoritative` | Markov-2 alpha sensitivity stable; canonical alpha 1; merged and swept |
| T1.9 | `superseded` | Divergent point estimate retained as history; do not use as final spanning claim |
| T1.9b | `authoritative` | Inferential rerun `newcomers_robust`; merged and decision-locked |
| T1.10–T1.20 | `authoritative` | Tracker marks complete; relevant outputs feed merged prose or later accepted tasks |
| T1.21 | `authoritative_supersession` | Diagnostic non-estimability is authoritative; original Tier 3 implementation goal superseded by T1.33–T1.35 |
| T1.22 | `deferred` | Formal mediation is outside the current paper; descriptive framing adopted |
| T1.23 / T1.23d | `authoritative` | Canonical paper-facing B9 result is OM-vs-GMM normalised ARI ≈0.31 with certified maximum bracket; earlier vacuous or sanity-bound normalisations are superseded |
| T1.24 / T1.24b | `authoritative` | Stored-metric SE/Wilson-CI result is canonical for Table 2 |
| T1.25 | `authoritative` | U-state sensitivity outcome merged with disclosure rule |
| T1.26 / T1.26b | `authoritative` | BHPS overlap/size-fraction result reviewed and merged |
| T1.27 | `authoritative` | 10-of-14 GMM sensitivity merged; branch history retained as needed |
| T1.28 | `prepared` | Sole open Stage 1 task; exact state in §6 |
| T1.29–T1.32 | `authoritative` | Completed panel/diagnostic work; preserve existing result and decision links |
| T1.33 | `authoritative` | FOO geometry signal supported but not topology-specific |
| T1.34 | `authoritative` | Final authority is the pre-registered `svyglm` fallback and transparency result |
| T1.34a-redo | `authoritative_supersession` | Partial feasibility failure is evidence justifying the fallback, not unfinished required work |
| T1.35 | `authoritative` | Corrected transparency supplement result; earlier defective power/sibling calculations superseded |
| T1.36 | `authoritative` | Frozen representation threading fix merged |
| T1.37 | `authoritative` | Frozen headline reruns and comparison merged; source of canonical Stage 1 headline values |

### 5.3 Superseded-result boundary

The authoritative supersession source is:

- `results/trajectory_tda_integration/stage1/SUPERSEDED.md`
- `results/trajectory_tda_bhps/stage1/SUPERSEDED.md`

These files prohibit citing the pre-frozen headline, sensitivity, and stratified results and identify their canonical replacements. Superseded JSONs remain in place because they are inputs to committed comparison and cleanup chains. They are excluded from claim authority but retained in provenance.

### 5.4 T1.6 closeout nuance

T1.6 is authoritative at the snapshot because the current Manager:

- independently checked the on-disk JSON rather than accepting the report alone;
- verified the pre-registered verdict mapping and key parameters;
- merged the result branch into local `main`;
- updated the Tracker and cleared the report bus.

The main-checkout task log remains internally stale: its frontmatter says `Complete`, while the body still says the run and verdict are pending. This is classified `stale_projection`; it does not overturn the committed result or Manager review. It becomes a priority eval fixture.

The Manager explicitly accepted the Worker's `[RESULT]` entry as the prose-lock landing because the pre-registration mechanically maps the result to the direction. W0 records that decision as current authority while leaving W5 to define whether future systems require a separate `[DECISION]` event.

## 6. T1.28 exact state

### 6.1 Governing design

T1.28 recomputes one subgroup-vs-own-Markov-1-null test for each of:

- gender: 2 subgroups;
- parental NS-SEC: 3 subgroups;
- birth cohort: 7 subgroups;
- both USoc and BHPS;
- BH correction separately within each 2/3/7 family;
- frozen row-subsets of the locked embeddings;
- exact W2 order 2/internal-p 2 plus the required landscape-L2 complement;
- `L=5000` with disclosed subgroup-specific actual landmarks;
- seed 42 and `B >= 1000` as currently written.

Authority:

- original pre-registration: `results/panel_methodology/fdr/pre_registrations_2026-06-13.json`;
- amendment: `results/panel_methodology/fdr/pre_registrations_amendment_2026-06-27.json`;
- task scope: `contracts/manifests/T1.28.yaml`;
- input provenance: `contracts/manifests/input-provenance/t128-inputs.yaml`;
- pending output contracts: the three `stratified-w2-*` schemas;
- task envelope: `.apm/bus/tda-agent/task.md`;
- worktree/branch: `.apm/worktrees/run-stratified-w2-perfamily-fdr`, `run/stratified-w2-perfamily-fdr`.

### 6.2 Verified non-execution state

At the snapshot:

- the task file is populated;
- the report bus is empty after T1.6 closeout;
- the worktree is clean and `.env` exists;
- input provenance is prepared;
- output contracts remain `pending:true` as intended before Worker binding tests;
- `tests/panel/test_t1_28_stratified_w2_contracts.py` does not exist in the worktree;
- `.apm/memory/stage-01/task-01-28.log.md` does not exist;
- no `stratified_w2_recompute_<date>.json` or `stratified_w2_bh_per_family_<date>.json` exists;
- no research compute process is active;
- delivery still requires the user's `/apm-4-check-tasks` invocation in the TDA Worker session.

T1.28 is therefore `prepared`, not `active`, `complete`, or `authoritative`.

### 6.3 Preconditions for Phase 1 closure

Phase 1 may close only after:

1. the current main changes needed by the Worker are integrated into the task branch or their absence is explicitly accepted;
2. a realistic preflight prices the complete subgroup design, including hidden null-null and observed-null work;
3. any projection beyond the task's guardrail causes a stop-and-escalate transition;
4. binding tests exist and task-specific contracts are no longer pending before producing results are committed;
5. representation, subgroup membership, FDR, dual-metric, and provenance requirements pass;
6. result JSONs are date-suffixed and independently reviewed;
7. any changed v1 claim is surfaced to Stephen before prose changes;
8. the result branch is merged or otherwise explicitly accepted;
9. task log, report bus, Tracker, and outcome/decision record agree;
10. the Manager confirms there is no other open Stage 1 requirement.

## 7. Phase 2 authority inventory

### 7.1 Merged Wave-1 authority

Eight Stage 2 task logs exist, all with `status: Success`; their commits are ancestors of `main`:

| Task | W0 class | Merged material |
|---|---|---|
| T2.1 | `merged_draft` | P01-A methods rewrite |
| T2.2 | `merged_draft` | P01-A H0/H2 results and caveat material |
| T2.3 | `merged_draft` | P01-A dimensionality/null narrative slice |
| T2.4 | `merged_draft` | P01-A escape regression and FOO section against canonical inputs |
| T2.5 | `merged_draft` | P01-A ARI and stability material, including canonical ≈0.31 normalised ARI |
| T2.6 | `merged_draft` | Mapper vocabulary and threshold sensitivity with caveats |
| T2.17 | `merged_draft` | P01-B spanning-identification result using T1.9b |
| T2.18 | `merged_draft` | P01-B single-machine reproducibility statement |

These sections are authoritative **draft inputs**. They are not equivalent to completed integrated v2 manuscripts.

### 7.2 Full Stage 2 incompleteness

The Plan defines twenty-two Stage 2 tasks and states that T2.22 is the v2-completion gate. No Stage 2 task log exists for:

| Task group | Current W0 state |
|---|---|
| T2.7 | Blocked on T1.28; §6.1 stratified W2/FDR prose not executed |
| T2.8 | Newly unblocked by T1.6; BHPS credibility rewrite not evidenced by a task log |
| T2.9 | Depends on T2.8; P01-A synthesis/abstract not evidenced |
| T2.10–T2.11 | P01-A supplement compilation and JRSS figures not evidenced |
| T2.12–T2.15 | P01-B methods sections not evidenced |
| T2.16 | P01-B §4.2 results rewrite not evidenced; contains the T1.6 credibility dependency |
| T2.19 | P01-B synthesis/abstract not evidenced |
| T2.20–T2.21 | P01-B supplement and figures not evidenced |
| T2.22 | Humanizer, cross-paper notation sweep, and `_project.md` completion update not evidenced |

The commit `a1e624f9` collapsed the Tracker's table after the eight Wave-1 tasks and wrote a memory summary saying “all eight Stage-2 prose Tasks are Done.” It did not amend the Plan's twenty-two-task scope or remove the T2.22 gate.

W0 therefore classifies:

- **Wave-1 subset:** complete and merged;
- **full Plan Stage 2:** incomplete;
- **Tracker label `Stage 2: Complete`:** `stale_projection` or narrowed-scope shorthand pending an explicit Manager/Stephen scope decision.

### 7.3 Phase 2 contingencies

- T2.17 openly carries a pending matched/age-stratified Betti robustness check. It is non-blocking for the current section but cannot be promoted to “confirmed” without the rerun.
- T2.18 is deliberately single-machine-scoped. It must not claim cross-machine bit-for-bit reproducibility until T0.3 completes.
- `papers/P01-A-JRSSA/_project.md` still contains some “pending User per-section review” wording even though the Wave-1 branch was later merged after approval. Commit ancestry and the Stage 2 summary outrank those stale checklist lines for the eight merged tasks.
- Neither paper's `_project.md` marks the complete Stage 2/T2.22 gate as closed. This agrees with W0's full-stage classification.

## 8. Legacy source map

### 8.1 Research authority

| Source | Role | Import treatment |
|---|---|---|
| `results/**/pre_registrations*.json` | Governing design and amendments | Import identity, version, parameters, decision rule, and source path |
| `contracts/**/*.yaml` plus binding tests | Machine-checkable research rules | Import contract version, ownership, pending/active state, and evidence |
| Committed result JSONs | Numerical evidence | Import manifest and hash; retain file in place |
| Input-provenance manifests | Input existence, identity, and vintage | Import as immutable evidence records |
| Computational Log `[RESULT]`, `[DECISION]`, `[NEGATIVE]` entries | Research interpretation and locks | Import selected authoritative entries with exact source anchor |
| `SUPERSEDED.md` manifests | Citable/non-citable boundary | Import as supersession events; never delete referenced files |
| Git commits and merge ancestry | Code and review lineage | Import commit IDs and relationships, not full diff text |

### 8.2 Coordination authority

| Source | Role | Caveat |
|---|---|---|
| `.apm/spec.md` | Approved project rules and scope | May contain historical text after later amendments |
| `.apm/plan.md` | Full task/dependency design | More complete than the collapsed Tracker for Stage 2 |
| `.apm/tracker.md` | Current coordination projection | Mutable, oversized, and sometimes stale |
| `.apm/memory/index.md` | Consolidated summaries and forward contingencies | Summary scope can be narrower than Plan scope |
| `.apm/memory/stage-*/*.log.md` | Worker execution narrative and evidence | May remain stale after autonomous completion or follow-up assembly |
| `.apm/bus/*/{task,report}.md` | Current delivery channels | Single-slot and overwrite-prone; empty or stale files are not history |
| worktree/branch registry | Execution isolation and active ownership | Must be inspected live, not reconstructed from Tracker prose |

### 8.3 Manuscript authority

| Source | Role | Caveat |
|---|---|---|
| `papers/P01-*/drafts/sections/*` | Section-level draft artefacts | Merged section does not imply final integrated manuscript |
| `papers/P01-*/_project.md` | Paper dashboard | Can lag merged work |
| reviewer-response plans | Acceptance criteria and issue mapping | Must be reconciled with later amendments/results |
| final versioned drafts | Submission-facing text | Not yet produced for the full v2 scope |

### 8.4 Source precedence

When records conflict:

1. governing pre-registration/decision plus committed result and contract evidence;
2. current code and binding tests;
3. Manager review and accepted commit ancestry;
4. task-specific log/report;
5. Tracker and memory summary;
6. paper dashboard;
7. historical narrative.

No single text file is a sufficient transition database.

## 9. Unresolved tasks and decisions

| ID | State | Required resolution | Blocks |
|---|---|---|---|
| T1.28 | `prepared` | Execute, review, merge, and reconcile all closeout records | Phase 1 closeout; T2.7; potentially §6.1 claim direction |
| Stage 2 scope conflict | `decision_required` | Decide whether the fourteen unlogged Plan tasks remain required or formally supersede them | Accurate Stage 2 state; W0 seal; T2.22 gate |
| T2.8 / T2.16 credibility prose | `ready_after_T1.6` | Integrate the accepted suspect/anti-conservative caveat | BHPS/P01-B results prose |
| T2.17 matched/age-stratified Betti check | `deferred_nonblocking` | Run or preserve explicit pending wording | Claim-strength upgrade only |
| T0.3 | `blocked` | Supply and verify second-machine canary | Cross-machine reproducibility claim; later repo gate |
| T2.18 cross-machine wording | `blocked_by_T0.3` | Upgrade only after T0.3 evidence | Stronger reproducibility statement |
| T2.22 | `not_evidenced` | Complete integrated humanizer, notation, and project-state gate after remaining prose | Stage 3 entry |
| Stage 3 | `not_started` | Repo extraction and provenance tables after v2 gate | Submission package |
| Stage 4 | `not_started` | Preserve as separate post-v2 follow-on unless scope is reconsidered | Future re-extraction programme |
| T1.6 task log | `stale_projection` | Optional historical correction/addendum; do not overwrite result authority | Operational consistency/eval fixture, not research conclusion |
| `[RESULT]` versus `[DECISION]` lock convention | `design_decision` | W5 must define when a deterministic pre-registered outcome mapping still requires a separate decision event | Successor scientific-authority model |

## 10. No-migration set

The following remain under legacy APM ownership until their stated boundary:

### 10.1 Active or blocked work

- T1.28 bus task, worktree, branch, contracts, inputs, future checkpoints, logs, reports, results, and decision handling;
- T0.3 `pipe/two-machine-check` worktree and any future canary;
- every remaining Plan-defined Stage 2 task and the T2.22 completion gate;
- Stage 3 reproducibility extraction and Stage 4 Option A re-extraction unless a later decision explicitly assigns them to the successor.

### 10.2 Retained worktrees and branches

- `run/stratified-w2-perfamily-fdr`: active preparation, must not be altered by ARS work;
- `pipe/two-machine-check`: paused legacy task, must remain intact;
- `run/bhps-markov1-credibility`: result merged but worktree retained for push/review/sweep cadence;
- `paper/p01-stage2-wave1`: merged history, cleanup candidate only after legacy review cadence;
- detached Codex worktrees under `C:\Users\steph\.codex\worktrees`: not APM migration inputs and not to be swept by W0.

### 10.3 Provenance-sensitive files

- all superseded Stage 1 JSONs named by the supersession manifests;
- comparison and denominator-cleanup inputs;
- existing exact-run checkpoint directories, including spanning-inference checkpoints;
- the Apr-8 recovery/orphan sequence material;
- gitignored null caches and frozen embeddings;
- external UKDA data, which must never enter a reusable template or standalone repository.

### 10.4 Current user-owned working-tree changes

W0 does not claim or modify existing `AGENTS.md`, `CLAUDE.md`, `.claude/skills/gitnexus/`, `.tmp.driveupload/`, recovery files, result checkpoints, or unrelated untracked artefacts. The Agentic Research System documents and narrow `.gitignore` exception are the only transition-workspace changes in scope.

## 11. Historical eval-fixture shortlist

Each fixture must retain an input state, expected failure before the control, and expected behavior after the control.

| Fixture | Historical evidence | Successor behavior to test |
|---|---|---|
| F-001 Single-slot overwrite | T0.3 bus overwritten by T0.12 | Immutable dispatch IDs preserve both tasks and reject destructive overwrite |
| F-002 Task/report collision | T1.28 task coexisted with an uncleared T1.6 report | Queue, acknowledgement, and review state remain distinct |
| F-003 Wrong control root | Main-checkout bus with worktree execution | Dispatch identifies control root, code root, result root, and cache root explicitly |
| F-004 Stale completion log | T1.6 log body remained “pending” after result merge | Generated projection detects disagreement and cannot present both as current |
| F-005 Narrowed stage collapse | Eight Stage 2 tasks collapsed while Plan retained twenty-two | Stage completion requires declared scope version and every required gate |
| F-006 Stale paper dashboard | `_project.md` lagged merged Wave-1 state | Dashboard is rebuildable from accepted events and flags manual drift |
| F-007 Hidden benchmark prerequisite | T1.6 benchmark performed uncapped null-null work | Benchmark mode caps every expensive prerequisite and emits early progress |
| F-008 Invalid parallel projection | Fewer timed evaluations than workers; threading held the GIL | Cost probe validates sample size, backend, scaling, and memory before extrapolation |
| F-009 Long-run guardrail | T1.6 exceeded 12h and later 48h thresholds | Guardrail produces explicit stop/input-required event and records user override |
| F-010 Downstream correction overreach | H2 grid correction nearly expanded PH design | Correction is classified by stage; valid upstream artefacts are preserved |
| F-011 Frozen-representation failure | Per-call PCA refit changed 21/50 cells | Representation contract blocks refit and records transform provenance |
| F-012 Null invariance | Label/cohort row shuffle left PH object invariant | Preflight demonstrates the null operation changes the tested input |
| F-013 Data-vintage incoherence | Apr-8 labels paired with May-2 sequence input | Input manifest rejects cross-vintage assembly before dispatch |
| F-014 Self-approved contract | Worker can author bindings, clear pending, implement, and produce | R2/R3 contract activation requires independent authority |
| F-015 Sanity value anchoring | ARI ≈0.40 lower-bound estimate displaced by certified ≈0.31 | Reviewer treats bounds as values to improve, not targets to reproduce |
| F-016 Code-review conceptual catch | Density-peak inversion passed earlier checks | Outcome and trajectory eval includes known-case and directionality assertions |
| F-017 Missing comparison fields | Sensitivity JSON omitted downstream fields | Schema validates consumer-required fields before result acceptance |
| F-018 Superseded-but-live provenance | Pre-frozen JSONs remain comparison inputs | Supersession removes claim authority without deleting source lineage |
| F-019 Result-to-claim overreach | Mapper “causal geography” language | Claim reviewer rejects causal wording without causal identification |
| F-020 Provider policy drift | Claude/Codex hook and guide differences | Semantic adapter-parity test fails when one runtime lacks a safeguard |

Priority for the first W6 catalogue: F-001 through F-005, F-007 through F-014, and F-020. They directly constrain W1/W2 architecture.

## 12. Legacy import policy

The successor should import a selected transition ledger, not the complete Tracker prose.

### 12.1 Import

- authoritative decisions and their governing pre-registrations;
- active dependencies and blockers;
- artefact identities, hashes, schema versions, and supersession links;
- accepted task/result state needed by future work;
- resource and worktree ownership for tasks still active at cutover;
- the historical eval fixtures in §11;
- explicit stale-projection records where they explain a required control.

### 12.2 Reference without normalizing

- full Tracker cell histories;
- completed Worker narratives;
- superseded computational arrays and JSONs;
- old reports and handoff prose;
- archived checkpoints not needed by active work.

These remain discoverable by path and commit.

### 12.3 Do not import

- external UKDA raw data;
- secrets or `.env` contents;
- transient MCP process state;
- orphaned runtime worktrees as if they were APM tasks;
- a “Stage 2 complete” event unless the scope conflict is resolved;
- a “Phase 1 complete” event before T1.28 acceptance.

## 13. Transition manifest

| Boundary object | Legacy status | Successor treatment |
|---|---|---|
| Phase 1 accepted results except T1.28 | Closed/accepted with supersession caveats | Import selected authority and provenance links |
| T1.28 | Prepared, not started | Legacy-owned; observe only until accepted |
| Wave-1 Stage 2 sections | Merged drafts | Reference as accepted draft artefacts |
| Remaining Stage 2 Plan tasks | Not evidenced/blocked | Legacy-owned pending scope decision |
| T0.3 | Paused | Legacy-owned blocker |
| Stage 3/4 | Not started | Remain legacy-planned until reassigned |
| Current contracts/provenance machinery | Active and valuable | Preserve behavior; redesign ownership and state interfaces |
| Mutable bus/Tracker | Operational legacy control plane | Compatibility view only after W2 implementation |
| Historical memories/logs | Evidence with known staleness | Reference by source; import selectively |
| Agentic Research System planning folder | New, review-pending | Successor design authority after Stephen accepts it |

## 14. Review gate

W0 is sealed only when the current Manager and Stephen confirm:

- [ ] T1.28 is the sole remaining Stage 1 task.
- [ ] T1.6's accepted `suspect / anti-conservative` result and lock handling are represented correctly.
- [ ] The grouped Phase 1 inventory does not promote a superseded result.
- [ ] The Wave-1/full-Stage-2 distinction is correct.
- [ ] The fourteen unlogged Stage 2 tasks are either retained or explicitly superseded in the Plan.
- [ ] T0.3, T1.28, remaining Stage 2 work, and provenance-sensitive files are in the no-migration set.
- [ ] The historical fixture shortlist captures the material control-plane and research-assurance failures.
- [ ] No active result, task, branch, worktree, cache, or paper claim is transferred to the successor prematurely.

## 15. W0 outcome and next gate

**W0 outcome:** `PARTIAL — manifest complete, legacy boundary not sealed`.

The partial status is intentional and evidence-based:

- T1.28 has not run;
- full Stage 2 scope is unresolved;
- the review gate is not yet signed.

W1 architecture work may begin against this manifest because its principal boundaries are known. W2 must preserve the unresolved-state and scope-version requirements exposed here. A final W0 addendum should be issued after T1.28 and the Stage 2 scope decision, rather than rewriting this snapshot silently.
