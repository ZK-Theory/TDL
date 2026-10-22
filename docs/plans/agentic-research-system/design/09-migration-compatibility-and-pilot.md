# W9 — Migration, Compatibility, and Pilot Specification

**Date:** 2026-10-22<br>
**Status:** `review_pending`; draft 0.1 for independent adversarial review (G7-B)<br>
**Specification version:** 0.1<br>
**Design authority:** accepted W1, W2, W4, W5, W6, W8; P-004, P-005, P-021, P-026, P-031, P-032, P-034, P-042,
P-047, P-050, P-056, P-058, P-061; the accepted 06u scope (D-1 to D-5, Stephen, 2026-10-21); the accepted G7-A W0
post-terminal addendum (revision 3, blob `1ebcf96f`) and W0-D1 to W0-D4 (Stephen, 2026-10-22)<br>
**Implementation authority:** None. This document creates no schema, command, projection, import, transition,
cutover, revocation, retirement, dispatch, compute or store state.<br>
**Review owner:** an independent adversarial reviewer in a distinct session; acceptance by Stephen of an exact
revision<br>
**Gate 7 item:** G7-B (06u §8.1); Jira KAN-13, with KAN-26

## 1. Decision summary and hard boundary

W9 defines how legacy (APM-era) research work enters the Agentic Research System (ARS) without contaminating either
side. Its first subjects are the two suspended papers, P01-A (JRSS-A) and P01-B (JRSS-B), with their results,
decisions, parked compute and coordination records.

The binding draft choices are:

1. **Import is observation, never adoption.** Legacy import produces content-addressed, read-only observations and
   projections only. No legacy task, bus record, tracker row, task log, result, claim or decision is copied or
   written into successor authority (handoff 07 §1; W2 §22.2).
2. **Three ownership modes, one writer.** Every legacy item is exactly one of `legacy_owned`, `successor_owned` or
   `closed_reference` (P-004). `dual_owned` is invalid. A path has one authoritative writer set at a time (06l §4).
3. **Transitions are per item, attributed and one way.** W9 reuses W11 §7.5's observation → source-inventory →
   mapping → transition chain for every legacy surface, not only Discovery. Allowed transitions are
   `legacy_owned → successor_owned`, `legacy_owned → closed_reference` and `successor_owned → closed_reference`.
4. **Status words carry no authority.** `Success`, `Done`, `Complete`, a merged branch, an empty bus, or a paper
   section is not evidence of acceptance (W2 §22.2; P-005). Status mapping (§6) assigns each legacy class a permitted
   successor treatment, and the class is taken from the accepted W0 series, not from the legacy record's own label.
5. **Field-level authority survives import.** A result file can be authoritative for one field family and
   superseded or unverified for another (G7-A §6.1). Import preserves the split; it never rounds a file to one class.
6. **Legacy compute runs as new successor work.** Parked legacy computations (T1.41, the Markov-2 α=1 recompute) do
   not reopen legacy Tasks. They run, if Stephen authorizes them, as new successor-owned Tasks that consume
   `closed_reference` legacy inputs, under their own pre-registration (§9; recommended answer to 06u §7 question 3,
   owner decision W9-D1).
7. **Rollback never returns authority to legacy.** Before a transition event commits, a stop leaves the item
   `legacy_owned`. After commit, recovery is successor-side; the only further move is to `closed_reference` (§12;
   reconciles 06l Step 5 with W11 §7.5, owner decision W9-D4).
8. **Accepted research evidence and decisions are never changed by migration or by its rollback** (02-roadmap W9
   review gate; P-026).

This is G7-B only. It does not open Gate 7, sign any W0 §14 item, inventory a file by handle, transition or cut over
anything, revoke a writer, retire a surface, dispatch work, or edit `papers/`, `.apm/` or the vault.

## 2. Entry criteria, evidence, boundaries, and consumers

### 2.1 Accepted decisions and assumptions

| Authority | W9 disposition |
|---|---|
| P-004 | Preserved: three modes; `dual_owned` invalid. |
| P-005 | Preserved: upgrading imported evidence from provisional to authoritative, R3 dispatch, decision reversal and claim promotion stay Stephen's. |
| P-021 | Preserved: no successor-owned Task shares a legacy mutable slot; compatibility views use registered ARS namespaces. |
| P-026 | Preserved with its "papers finish under APM" premise amended by the 06u/handoff 07 direction: the legacy boundary holds until per-item transition; G7-C records the wording. |
| P-031, P-050, 06s §4 | The Gate 6 fresh SPEC-01 run is the pilot evidence W9 consumes (§13). SCALE-01 is not a condition (06u D-2). |
| P-032 | Preserved: ARS is canonical for successor Discovery objects; W11 owns Discovery semantics; W9 sequences the legacy side. |
| P-034 | Preserved: consolidation by per-item transition, never dual-running or bulk import. |
| P-042 | Governs dispatch: operator-mediated external sessions; ARS never invokes a provider. P-033 is superseded (06g §2). |
| P-047 | Gate 9 owns RM-04's manuscript-review pilot and manuscript-specific use decision (§10). |
| P-058, P-061 | Gate 6 known limits and the SPEC-01 continuation are inputs, not W9 scope (§3.3). |

Bounded assumptions, each explicit:

- **W9-A1 — W11 acceptance.** W9 assumes W11's §7 transition design is accepted before any W9 transition runs. W11
  is `review_pending` revision 0.5 in its own header, with D-G6-4 limb 1 open, while Jira KAN-19 is Done (06u D-10).
  W9's dependency is on the accepted W11 text, whichever record settles it.
- **W9-A2 — W11 runtime.** The W11 transition commands are not implemented. On `3fa437a1` the repository contains
  only `tools/verify_w11_materialization.py` and `.research-system/evals/expected/w11-portfolio-discovery-v1.json`
  naming them; no handler implements `LegacyRecordObserved`, `TransitionPortfolioOwnership`,
  `LegacySourceInventory` or `CutOverDiscoveryPath`. Every W9 transition therefore waits on an implementation plan
  that is outside this document.

### 2.2 Direct evidence inputs

| Evidence | Use in W9 |
|---|---|
| `transition/W0-legacy-closeout-transition-manifest-2026-06-28.md`, the 2026-06-29 addendum, and the accepted post-terminal addendum (G7-A, `1ebcf96f`) with its acceptance record | Authority classes (manifest §4), source precedence (§8.4), import policy (§12), no-migration set (§10 and G7-A §12), the re-derived Stage 1 classes (G7-A §6.1), the Stage 2 classes (§9), post-freeze writes (§11), the A-001 list (§10) |
| `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md` | Per-file draft verdicts, the citable-artifact list (§3.2), holes H1–H9 |
| `docs/plans/strategy/P01-Adversarial-Mathematical-Review-2026-07-18.md` (#132) | A1–A4 and the "no rung-4/5 claim promotion before A1 and calibration" condition |
| `docs/plans/strategy/APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md` | Invariants I1a–I11a as enforcement requirements on Gate 7 deliverables |
| `docs/plans/strategy/Theorem-Derived-Invariant-Battery-2026-07-18.md` (#131) | The P2 double-null harness as T1.41's calibration route |
| `results/trajectory_tda_integration/stage1/SUPERSEDED.md` and `w2_fallback_audit_2026-07-14.json` | Field-family supersession; the line-69 import conflict (G7-A §8) |
| Design W1 §W9, W2 §§14, 22, W11 §7 | Ownership modes, compatibility views, import envelope, transition and cutover machinery |
| `implementation/06l-wp6-7-legacy-consolidation-sequencing.md` | Steps 0–7, path rules (§4) |
| `implementation/06u-gate7-prep-current-state-scope-note.md` | The accepted Gate 7 scope, the intake manifest (§6) and the §7 dispatch questions |
| 02-roadmap W9 | The required contents: import format and status mapping, `.apm/` views, pilot rubric, rollback and stop, metrics, review points, deprecation path |

### 2.3 Boundaries and consumers

| Boundary | W9 rule | Consumer |
|---|---|---|
| W2 control plane | Sole mutation boundary; W9 adds no command, only requirements on W2/W11 commands | Future implementation plan |
| W11 | Owns Discovery object semantics and the transition/cutover machinery W9 reuses | Portfolio Steward; migration authority |
| W5 | Owns assurance requirements, claim candidates and claim promotion; W9 never promotes | Assurance engine; claim reviewer |
| W6 | Owns `gate_stage: pilot_promotion` and its fixtures (§11) | Eval runner |
| W8 | Owns resource grants for any successor compute W9 sequences | Operator |
| W10 | Not consumed; no TDL path becomes mandatory for W10 | — |
| Legacy surfaces | Read-only observation until an item's accepted transition (§4) | Humans; migration authority |

### 2.4 Design-entry-criteria disposition

| README criterion | Draft 0.1 disposition |
|---|---|
| 1. Decisions accepted or assumptions explicit | Satisfied for authorship: §2.1 table and W9-A1, W9-A2; owner decisions W9-D1 to W9-D8 are open (§15). |
| 2. Evidence inputs in the evidence register | **Partly.** §2.2 lists direct sources. The root evidence register `01-current-system-evidence.md` has no dated W9 addendum; one is needed before acceptance (W9-D8 asks where it lands). |
| 3. Boundaries and consumers | Satisfied: §2.3. |
| 4. Independent review owner | Satisfied for assignment: an independent session reviews this draft; Stephen accepts an exact revision. |
| 5. Acceptance tests before implementation | Satisfied for specification: §16 lists the test families; none is materialized. |

## 3. Scope

### 3.1 Legacy surfaces W9 governs

From W0 manifest §8 and G7-A §11:

| Surface | Paths (repository-relative unless noted) | Current owner and writer |
|---|---|---|
| Research authority | `results/**` result JSONs, `results/**/pre_registrations*.json`, `results/**/SUPERSEDED.md`, `contracts/**` with binding tests, input-provenance manifests | `legacy_owned`; writer: APM lane (frozen), plus the post-freeze writers G7-A §11 records |
| Decision record | Vault `04-Methods/Computational-Log.md` legacy entries (P01, P04, T-numbered), `CONVENTIONS.md` locks | `legacy_owned` for legacy entries; the log is append-only and shared by successor entries (§7.3) |
| Coordination | `.apm/spec.md`, `.apm/plan.md`, `.apm/tracker.md`, `.apm/memory/**`, `.apm/bus/**` | `legacy_owned`; writer: APM (frozen), plus the #368 Working-Note append |
| Manuscripts | `papers/P01-A-JRSSA/**`, `papers/P01-B-JRSSB/**`, `papers/shared/**` | `legacy_owned`; writer: APM prose lane (frozen since 2026-07-18), plus #277's lint edit |
| Retained branches | `paper/p01a-dedup-rewrite`, `pipe/two-machine-check`, and the others G7-A §12 lists | `legacy_owned` |
| Discovery | Vault `00-Meta/Discovery/_backlog.md` and active Discovery items | `legacy_owned`; W11 governs; W9 sequences (§14) |

### 3.2 Out of scope

- Implementing any W2/W11 command, projector or guard.
- Deciding any research question the intake manifest carries (A1 fork, H3, A2 construction, Stage 2 scope).
- Manuscript authoring.
- Provider invocation or credential handling (P-042).

### 3.3 The SPEC-01 continuation

P-061's continuation (06u §6.2) is ARS-native work on an ARS-created Candidate. It is not a legacy item and needs no
W9 transition. W9 touches it only where it reads legacy material: the R4 crosswalk documentation task reads BHPS/USoc
documentation, which is external reference material, not a legacy-owned surface. Its dispatch bar is its own (06u
D-3).

## 4. Path and writer registry (KAN-26)

Every legacy surface in §3.1 is registered with an explicit writer set before any transition touches it. W11 §7.2's
`PathRegistration` is the record; W9 extends its `role` enum with `legacy_research_authority`,
`legacy_coordination` and `legacy_manuscript`, each `ownership_mode: legacy_owned`.

### 4.1 Writer sets observed

G7-A §11 shows that the writer set of a legacy path is wider than "the APM lane":

| Writer observed after the freeze | Example | Effect |
|---|---|---|
| Repo-wide tooling change through a reviewed PR | #277 lint edit to three `papers/` files | Formatting and unused imports; behaviour-preserving |
| Session Working Note through a reviewed PR | #368 appended to `.apm/tracker.md` | Coordination note; no Task row edited |
| Owner-ruled result commit after the freeze merge | `1af52f6d` (H6) | Explicit User ruling |
| **Direct push to main with no PR** | `5df0c001` (seven result files), `811d5a2b` (three input-provenance manifests) | Line endings and manifest rewrites; restored by #219; net nil |

### 4.2 Required rule

For a path with `ownership_mode: legacy_owned`:

1. **Allowed writer classes:** (a) a legacy-lane commit that the freeze permits (none, while the freeze stands); (b) an
   attributed, reviewed repository-wide change that changes no research value and records an owner note naming the
   legacy paths it touched; (c) an explicit owner ruling recorded in the decision log.
2. **Prohibited:** any successor (ARS) writer; any unreviewed write, including a direct push with no PR; any write
   during an item's transition window (§8.3).
3. **Detection:** a mechanical guard is required before the first transition (owner decision W9-D5). Its negative
   control is a fixture commit touching a registered `legacy_owned` path without an owner note, which must fail.
   The guard is a requirement on the implementation plan, not built here.

### 4.3 Preparation, transition, cutover and retirement matrix (KAN-26)

| Class of action | Allowed now | Required before it |
|---|---|---|
| Preparation: documents, read-only observation, inventory design, rollback and collision design, templates | Yes | — |
| Per-item transition (06l Step 5) | No | Gate 7 opened (06l Step 1, D-1 bar); accepted G7-A, G7-B, G7-C; accepted W11 (W9-A1) and implemented transition commands (W9-A2); the W9-D5 guard; for an affected item, A-001 signed and the Stage 2 scope decided (W0-D1, W0-D2); the item's applicable `pilot_promotion` evidence (§11); Stephen's batch approval (D-G6-4 limb 2) |
| Whole-path cutover (06l Step 6) | No | Every item on the path transitioned; writer revocation; final observation; W11 §7.6 closure; Stephen's `legacy_path_cutover` Decision |
| Retirement (06l Step 7) | No | Durable cutover; no live reference as authority; Stephen's retirement decision |
| Discovery items at Step 3 or later | No | **G7-B's Discovery inventory accepted** (W0-D4 condition; §14) |
| OR-032/OR-033, provider calls, research execution, eligibility change, claim promotion | No | Their own gates |

## 5. Import format

Every import is a W2 §22.1 import envelope, recorded as a W11 §7.5 `LegacyRecordObserved` artefact bound to a
handle-verified read (W11 §7.3). W9 generalizes the observation's `source kind`:

| Source kind | Observed unit | Selector |
|---|---|---|
| `result_json` | One committed result file, with its Git blob and SHA-256 | Whole file, plus field-family selectors (§6.2) |
| `supersession_manifest` | One `SUPERSEDED.md` entry | Byte range of the entry |
| `pre_registration` | One pre-registration file and its amendments | Whole file |
| `contract` | One contract YAML with its pending/active state and binding test | Whole file |
| `decision_entry` | One Computational-Log entry | Byte range from heading to separator |
| `tracker_row` | One `.apm/tracker.md` row | Byte range of the row |
| `task_log` | One `.apm/memory/stage-NN/` log header | Frontmatter block |
| `manuscript_file` | One file under `papers/P01-*/` | Whole file |
| `discovery_row` | One `_backlog.md` row | W11 §7.6.1 row selector |

Each observation records: importer identity and version; source path, commit and blob; observed time; the W0
authority class **as accepted in the W0 series**, not as the source labels itself; parsed aliases; open conflicts;
and the explicit list of what was not inferred.

## 6. Status mapping

### 6.1 Class to treatment

| W0 class (manifest §4, G7-A) | Permitted successor treatment |
|---|---|
| `authoritative` | Eligible for `closed_reference` by an attributed transition. Never re-accepted as a successor result; cited by reference. |
| `authoritative_supersession` | `closed_reference`; imported as a supersession relation, never deleted. |
| `merged_draft` | Remains `legacy_owned` until its paper's transition (§10). Carries the claim-trace audit's per-file verdicts as qualifiers; never imported as accepted prose. |
| `prepared`, `active` | Remain `legacy_owned` (none exist at `3fa437a1`). |
| `blocked` | Remains `legacy_owned`; the blocker is imported as an observation. |
| `deferred` (parked for ARS) | The legacy row may move to `closed_reference`. Its work re-enters only as a new successor-owned Task (§9). |
| `superseded` | `closed_reference` with its supersession lineage; never cited as current. |
| `stale_projection` | Observation only. Its content is never imported as state; the stronger record it contradicts governs. |
| `unverified` | `closed_reference` with an `unverified` qualifier; upgrading it needs P-005 approval and the evidence the class names. |

### 6.2 Field-family authority

When the accepted W0 series classes a file per field family, the import keeps one class per family. Examples from
G7-A §6.1:

| Object | Families and classes |
|---|---|
| `usoc_headline_frozen_2026-05-28.json`, `bhps_headline_frozen_2026-05-28.json` (T1.37) | H₀ W₂ and landscape L² `authoritative`; H₁ W₂ `superseded` by the 2026-07-14 corrected files |
| `stratified_markov1_W2_L5000_frozen_2026-05-29.json` (T1.3) | H₀ W₂ and landscape L² `authoritative`; H₁ W₂ `unverified` |
| `bhps_nonoverlap_reanalysis_2026-06-09.json` (T1.26b) | Landscape `authoritative`; H₁ W₂ `superseded` (falsified 2026-07-16) |
| Markov-2 α=1 cell JSONs (H6) | Landscape L² `authoritative`; W₂ do-not-cite |
| `markov2_alpha_sweep_summary_2026-06-16.json` (T1.8) | W₂ `unverified` (UNVERIFIABLE per T1.38 Phase 1) |

A selector that cannot address a family separately blocks import of that file (`field_family_unaddressable`).

### 6.3 Source precedence and the `SUPERSEDED.md` conflict

Conflicts resolve by manifest §8.4 precedence: governing decision plus committed result evidence, then code and
binding tests, then Manager review and ancestry, then task log, then tracker and memory, then dashboard, then
narrative.

`SUPERSEDED.md` line 69 calls the Markov-2 summary "presumed IMMUNE", while the T1.38 Phase 1 `[RESULT]` and
`w2_gap_closure_phase1_2026-07-16.json` record it as UNVERIFIABLE (G7-A §8). The import takes UNVERIFIABLE. The
observation of line 69 is recorded with a `superseded_by_precedence` conflict that names both records. The legacy
file is not edited.

### 6.4 Known record errors

G7-A H10: the 2026-07-11 T1.20 `[DECISION]` quotes Tier 1 NS-SEC odds ratios from the do-not-cite 05-13 file; a dated
correction entry (2026-10-22) supersedes those numbers. An import of that decision entry must bind the correction
entry and must not carry the stale values.

## 7. Compatibility views

### 7.1 `.apm/`

The APM lane is frozen, and no unmodified APM Worker is active. W9 therefore defines **no** `.apm/` compatibility
writer. The W2 §14.3 namespace `.apm/bus/<agent>/ars/` stays reserved and unregistered. If a later decision reactivates
an APM Worker, the task it touches stays `legacy_owned` (P-021).

### 7.2 Read-only legacy projection

ARS may publish a read-only projection of imported legacy observations under a registered ARS namespace (proposed
`.research-system/projections/legacy/`, owner decision W9-D8 together with the evidence-register question). It carries
W11 §7.7's source position, projector version, content hash and rebuild identity, and it is never an input to an
authority predicate.

### 7.3 The decision log

The vault Computational-Log is one append-only file written by legacy and successor sessions alike. It cannot be a
single-writer path today. W9 treats each legacy entry as a separately observed `decision_entry` (§5) and requires
that successor sessions append only new entries, never edit a legacy entry. Corrections are new dated entries, as
G7-A H10's was. A whole-path cutover of the log is not proposed.

## 8. Per-item ownership transition

### 8.1 Mechanism

W9 uses W11 §7.5 unchanged for every source kind in §5:

```text
LegacyRecordObserved (handle-bound)
  -> accepted LegacySourceInventoryContent for the source path
  -> accepted legacy-transition mapping content (one source row -> target mode and objects)
  -> TransitionPortfolioOwnership
  -> PortfolioItemOwnershipTransitioned
```

The legacy file is not edited by a transition. The transitioned item's exact source bytes become frozen lineage.

### 8.2 Item granularity

| Legacy surface | Item | Target mode |
|---|---|---|
| A result file | The file, with field-family classes | `closed_reference` |
| A pre-registration, contract or supersession entry | The file or entry | `closed_reference` |
| A legacy decision entry | The entry | `closed_reference` |
| A tracker row or task log | The row or log | `closed_reference` |
| A parked legacy computation | Its tracker row | `closed_reference`; the work re-enters as a new successor Task (§9) |
| A paper | The whole paper root (`papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/`) | `successor_owned`, by whole-path transition only (§10; owner decision W9-D6) |
| `papers/shared/` | The directory | Stays `legacy_owned` until both papers have transitioned |

### 8.3 Transition window

From the source observation to the transition event, the item's source path must have no write. A write detected in
the window aborts the transition with no event (W11 §7.5). The W9-D5 guard covers this window.

### 8.4 Preconditions per item

An item transitions only when all of these hold:

1. §4.3's transition column;
2. for a paper or any item feeding a claim, the A-001 list items that block it are resolved (G7-A §10);
3. for a result family, its field-family classes are imported as in §6.2;
4. for any item whose transition would accept evidence, change citability or advance a claim, the applicable
   `pilot_promotion` evidence (§11);
5. an independent item review and Stephen's acceptance; the producing actor cannot establish its own independence.

## 9. Parked legacy compute

### 9.1 The route (recommended; W9-D1)

T1.41 and the Markov-2 α=1 recompute run, if authorized, as **new successor-owned ARS Tasks**:

1. The legacy tracker rows move to `closed_reference` with lineage (§8.2). No legacy Task is reopened.
2. The new Task's inputs are `closed_reference` legacy artefacts (embeddings, null caches, checkpoints), bound by
   content address and W8 grants.
3. The new Task has its own pre-registration, filed before dispatch, which supersedes nothing in the legacy record.
   For the Markov-2 recompute this is an amendment of the 2026-07-17 pre-registration for review finding A1 (06u
   D-7; G7-A §6.2). For T1.41 its design answers A3, and may answer A1 and A2 in the same campaign.
4. Its result is a successor artefact. A legacy-owned paper cannot cite it until the paper transitions (§10); the
   result does not write into `results/` legacy paths.

**Alternative rejected:** transitioning each paper first and running the compute inside the paper's successor scope.
That delays the calibration that every rung-4/5 claim needs (review A3) behind the manuscript capability (§10).

### 9.2 Dispatch model

| Question (06u §7) | W9 treatment |
|---|---|
| Q1: is Gate 7 inside P-042's "first release"? | Owner decision **W9-D2**. Recommendation: yes; Gate 7 dispatch is operator-mediated under P-042, as Gate 6's was, and live-provider reactivation is not required. |
| Q2: does P-029's two-family R3 rule bind operator-mediated sessions? | Owner decision **W9-D3**. Recommendation: yes for any review that gates a claim promotion; the operator starts one review session on a second model family (for example Codex), and if none is available the item records `r3_family_coverage_insufficient` and waits. Gate 6's one-family reviews are a P-058 known limit, not a precedent. |
| Q3: how legacy compute runs under P-026 | §9.1 |

D-G5-1(a) still blocks M/H model-graded acceptance; review stays deterministic gates, independent agents and Stephen.

## 10. Manuscripts

The papers are the last items to transition, because they consume everything else.

1. A paper transitions as one whole root (§8.2; W9-D6). Per-section transition would split one manuscript across two
   writers.
2. Before a paper transitions:
   - every A-001 item that feeds one of its claims is resolved or explicitly scoped out by Stephen;
   - the Stage 2 scope decision (W0-D2) covers its rows;
   - the claim-trace audit verdicts and the §6.2 HOLD are carried as qualifiers;
   - the review's A1 fork is decided and the double-null calibration has run, for any rung-4/5 claim the paper keeps
     (Computational-Log 2026-07-18).
3. **Manuscript review depends on Gate 9.** P-047 places RM-04's manuscript-review pilot and the manuscript-specific
   use decision at Gate 9. Owner decision **W9-D7**: either a paper's transition waits for that capability, or Stephen
   accepts a named interim manuscript-review route for P01-A and P01-B. Recommendation: wait for the Gate 9 capability
   for prose; let compute (§9) and result-family imports (§6) proceed first.
4. Prose resumes only under an ARS workflow enforcing register and claim-to-artifact binding (CONVENTIONS freeze lock).

## 11. Per-item `pilot_promotion` condition (06u D-1)

Gate 7's opening bar is 06s §4 closure evidence (D-1). W6's `gate_stage: pilot_promotion` evidence moves to a
per-item dispatch condition: an item whose transition or dispatch would accept research evidence, change a result's
citability or advance a claim needs the applicable fixtures produced or explicitly waived by Stephen.

| Fixture (W6 §§ catalogue; 06b) | Applies to |
|---|---|
| S-005 comparative conflict | Any item where two results compete for one object (for example the T1.3 source and the 2026-05-13 battery) |
| S-007 stale review hash | Every item review |
| S-014 backup, restore and machine move | The first transition batch (store identity across the batch) |
| S-015 supersession cycle | Every import of a supersession relation |
| S-016 R3 provider outage | Any claim-gating review under W9-D3 |
| F-037 Partial, negative, superseded and claim-promotion separation | Every result-family import and every paper transition |
| F-038 domain-pack and qualitative applicability boundary | Any item that uses the TDA pack's assurance lanes |

## 12. Rollback and stop criteria

### 12.1 Rollback

06l Step 5 says rollback "returns the item to its prior authority". W11 §7.5 says no transition returns to
`legacy_owned`. W9 reconciles them (owner decision **W9-D4**; recommended):

- **Before the transition event commits**, any stop leaves the item `legacy_owned`, with no event and no change to the
  legacy file.
- **After commit**, rollback is successor-side: the successor object is rebuilt, corrected by a new attributed event,
  or moved to `closed_reference`. Authority never returns to `legacy_owned`, and the legacy file is never edited.
- In both cases no accepted research artefact, result or decision changes (02-roadmap W9 review gate).

G7-C carries the 06l Step 5 wording change.

### 12.2 Stop criteria

Stop a transition, batch or pilot when any of these holds:

- a legacy record would be imported as accepted state, or a status word would stand in for evidence;
- a path would have two writers, or the W9-D5 guard is absent or has not been watched to fail;
- a field family cannot be addressed separately (§6.2);
- a precedence conflict (§6.3) is unresolved;
- an item review is not independent of its producer, or is on a stale hash (S-007);
- a claim-gating review lacks second-family coverage under W9-D3;
- a source path changes during an item's transition window;
- operator burden makes routine bypass of a control likely (04-plan §7).

## 13. Pilot rubric, baseline and comparison metrics

### 13.1 The pilot already run

The Gate 6 fresh SPEC-01 run (P-058) is the system pilot under P-031's amended occupant rule. Against 04-plan §6's
promotion criteria (06u §5.1):

| Criterion | Gate 6 evidence | Status |
|---|---|---|
| Deterministic replay and recovery | Replay, backup, evidence-only restore, frozen-checkout replay | Met |
| No silent overwrite or ambiguous authority | Append-only ledger, replay through the tail | Met |
| Complete provenance | Hash-pinned scripts; evidence index | Met |
| Required scientific and operational graders | Independent reviews, approve-only, one model family; D-G5-1(a) | Partly met |
| Smaller context without reduced governing-evidence recall | Not measured | **Open** |
| Acceptable operator burden | Not measured; the live steps ran 2026-10-16 to 2026-10-21 | **Open** |
| Stephen's approval for R3 or claim transitions | Every owner point | Met |

### 13.2 Gate 7 integration pilot

The first accepted transition batch (06l Step 4, D-G6-4 limb 2) is the integration pilot. It measures:

| Metric | Measure | Source |
|---|---|---|
| Context size | Tokens in each item's compiled context packet against the legacy Manager bundle for the same item | W3 manifests |
| Governing-evidence recall | Fraction of the item's governing records (G7-A §6–§10) present in its packet | Reviewer checklist |
| Operator burden | Owner actions and wall time per transitioned item | Owner log |
| Defects | Review findings per item by severity | Review records |
| Recovery | Replay and restore after the batch | W8 evidence |

No target value is set here. Stephen sets acceptance thresholds before the batch runs, and they are not chosen after
the outcome.

## 14. Discovery inventory (W0-D4)

W0-D4 assigns the Discovery boundary to G7-B, against W11. This section specifies it; the accepted inventory itself is
a W11 `LegacySourceInventoryContent` (§7.6.1), which only an implemented W11 runtime can produce with its handle-bound
read and independent reproducer.

| Part | Content |
|---|---|
| The legacy path | Vault `00-Meta/Discovery/_backlog.md`, `legacy_owned`, legacy-written (W11 §7.1). Last recorded inspection SHA-256 `37eec1ba…` (2026-07-18, W11 §2.2), a dated observation, not an identity. This track has not read it. |
| Items named in the record | The registered sheaf-Laplacian dispatch and the MCbiF decision-pending battery (P-032); WT-2 and WT-3 (freeze handoff §3, parked as ARS-native candidates); the MCbiF confirmatory batteries (Computational-Log 2026-07-16, labelled P01, and 2026-07-18, labelled P04) |
| ARS-created Discovery objects | The SPEC-01 Candidate `obj_a9ba6213-…` is already `successor_owned` in the Gate 6 store; it is not a legacy item |
| Condition | No Discovery item takes a 06l Step 3 or later action until this inventory is accepted (W0-D4). This section's acceptance is the G7-B-level acceptance; the per-item transitions still need the W11 inventory. |

Owner decision **W9-D8** also covers whether a read-only, dated observation of `_backlog.md` should be added to this
section before acceptance. It would not replace the W11 inventory.

## 15. Owner decisions

| ID | Decision | Recommendation |
|---|---|---|
| W9-D1 | Route for parked legacy compute (§9.1) | New successor-owned Tasks consuming `closed_reference` inputs; legacy rows to `closed_reference` |
| W9-D2 | Gate 7 dispatch inside P-042's first release (06u §7 Q1) | Yes; operator-mediated |
| W9-D3 | Two-family review for claim-gating reviews (06u §7 Q2) | Yes; otherwise `r3_family_coverage_insufficient` |
| W9-D4 | Rollback semantics (§12.1) | One way, per W11; G7-C amends 06l Step 5 |
| W9-D5 | A mechanical guard on writes to `legacy_owned` paths, including direct pushes with no PR (§4.2) | Required before the first transition, with a negative control |
| W9-D6 | Paper granularity (§8.2, §10) | Whole paper root |
| W9-D7 | Manuscript review before Gate 9 (§10) | Wait for the Gate 9 capability for prose |
| W9-D8 | Where the W9 evidence addendum and the legacy projection namespace land, and whether to observe `_backlog.md` now (§2.4, §7.2, §14) | A dated addendum to `01-current-system-evidence.md`; `.research-system/projections/legacy/`; defer the backlog observation to the W11 inventory |

## 16. Acceptance-test families (specification only)

| ID | Invariant | Negative control |
|---|---|---|
| W9-T1 | A legacy status word never produces `TaskAccepted`, `DecisionResolved` or `CompleteScope` | Import a `Done` tracker row; no acceptance event |
| W9-T2 | Field-family classes survive import | Import T1.37's headline file; the H₁ W₂ family is `superseded`, not `authoritative` |
| W9-T3 | Precedence resolves `SUPERSEDED.md` line 69 to UNVERIFIABLE | Import line 69 alone; the conflict blocks rather than importing "presumed IMMUNE" |
| W9-T4 | No transition returns to `legacy_owned` | Submit `successor_owned → legacy_owned`; schema rejects |
| W9-T5 | A write in the transition window aborts the transition | Write the source path after observation; no event |
| W9-T6 | The legacy-path guard fires on an unattributed write | Fixture commit to a `legacy_owned` path without an owner note; guard fails |
| W9-T7 | Parked compute creates a new successor Task and reopens no legacy Task | Attempt to reopen T1.41's legacy row; rejected |
| W9-T8 | A claim-gating review without second-family coverage blocks | One-family review on a claim-gating item; `r3_family_coverage_insufficient` |
| W9-T9 | A corrected legacy decision imports with its correction | Import the 2026-07-11 T1.20 entry; the Tier 1 values come from the 2026-10-22 correction |
| W9-T10 | Rollback after commit changes no accepted artefact | Roll back a transitioned result family; every legacy blob unchanged |

## 17. Independent review and exit gate

- [ ] Independent adversarial review of this exact revision in a distinct session.
- [ ] Author reconciliation of every finding.
- [ ] Stephen's decisions W9-D1 to W9-D8.
- [ ] Stephen's acceptance of the exact reconciled revision.
- [ ] The evidence-register addendum (§2.4).

Acceptance of W9 opens nothing, transitions nothing and authorizes no implementation.
