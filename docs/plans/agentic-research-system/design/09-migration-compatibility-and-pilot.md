# W9 — Migration, Compatibility, and Pilot Specification

**Date:** 2026-10-22<br>
**Status:** `review_pending`; draft 0.2, reconciling the independent review of draft 0.1
(`reviews/g7b-w9-draft-0-1-review-97f71c19-2026-10-22.md`, REWORK REQUIRED). Dispositions:
`reviews/g7b-w9-reconciliation-2026-10-22.md`.<br>
**Specification version:** 0.2<br>
**Design authority:** accepted W1, W2, W3, W4, W5, W6, W7, W8 and W11 (revision 0.5, blob `f90729d0`, D-G6-4 limb 1,
2026-08-01); P-004, P-005, P-021, P-026, P-028, P-029, P-031, P-032, P-034, P-042, P-047, P-050, P-058, P-061; the
accepted 06u scope (D-1 to D-5); the accepted G7-A W0 post-terminal addendum (revision 3, blob `1ebcf96f`) and W0-D1
to W0-D4; Stephen's choice of schema route (ii), 2026-10-22 (§2.1)<br>
**Implementation authority:** None. This document creates no schema file, catalogue, command, projection, import,
transition, cutover, revocation, retirement, dispatch, compute or store state.<br>
**Review owner:** an independent adversarial reviewer in a distinct session; acceptance by Stephen of an exact
revision<br>
**Gate 7 item:** G7-B (06u §8.1); Jira KAN-13, with KAN-26

## 1. Decision summary and hard boundary

W9 defines how legacy (APM-era) research work enters the Agentic Research System (ARS) without contaminating either
side. Its first subjects are the two suspended papers, P01-A (JRSS-A) and P01-B (JRSS-B), with their results,
decisions, parked compute and coordination records.

The binding draft choices are:

1. **Import is observation. Adoption is a separate, Stephen-only decision.** Legacy import produces
   content-addressed, read-only observations. Nothing legacy reaches successor use until an `AdoptLegacyAuthority`
   decision (§9) binds it under P-005. "Citation by reference" is not a use.
2. **Three ownership modes, one writer, with two declared exceptions.** Every legacy item is exactly one of
   `legacy_owned`, `successor_owned` or `closed_reference` (P-004). A registered legacy file has one writer set. The
   Computational-Log and `CONVENTIONS.md` are the two files that cannot meet that rule today; they are handled by a
   bounded exception (§7.3, owner decision W9-D9).
3. **W9 owns its own closed schema family** (route (ii)). It reuses W11's observation → inventory → mapping →
   transition pattern, with its own registration root, selectors, target kinds and catalogue. It neither extends nor
   reopens W11, whose accepted catalogue was genesis-imported into the Gate 6 store.
4. **Two observation paths.** Items that only ever become `closed_reference` use a light path: a handle-bound
   observation, an independent review, and Stephen's batch decision (§8.1). Items that become `successor_owned` (the
   paper roots) use the full transition chain (§8.2).
5. **Field-family authority survives import.** Families are addressed by JSON-pointer sets from an independently
   authored membership table, not by byte ranges (§6.2).
6. **Classes come from signed records.** An observation may carry a W0 class only after Stephen has signed the
   manifest §14 items it depends on (W0-D1).
7. **Legacy compute runs as new successor work** on a new pre-registration, with inputs regenerated from committed
   scripts or referenced by hash. No legacy Task, pre-registration or result is reopened or written (§10).
8. **Rollback never returns authority to legacy, and never strands a paper.** Before commit, a stop leaves the item
   `legacy_owned`. After commit, recovery is successor-side, including a defined recovery route for a transitioned
   paper (§13).
9. **Accepted research evidence and decisions are never changed by migration or by its rollback** (02-roadmap W9
   review gate).

This is G7-B only. It does not open Gate 7, sign any W0 §14 item, register or observe any file, transition or cut
over anything, revoke a writer, retire a surface, dispatch work, or edit `papers/`, `.apm/` or the vault.

## 2. Entry criteria, evidence, boundaries, and consumers

### 2.1 Accepted decisions and assumptions

| Authority | W9 disposition |
|---|---|
| P-004 | Preserved: three modes; `dual_owned` invalid. |
| P-005 | Preserved and applied: adoption (upgrading imported evidence), pre-registration changes, R3 dispatch, decision reversal and claim promotion stay Stephen's. |
| P-021 | Preserved: no successor-owned Task shares a legacy mutable slot. |
| P-026 | **Amended through G7-C.** Its legacy boundary holds until per-item transition; its "papers finish under APM" premise and 04-plan §2/§5's "never migrated into the prototype … never used as live pilot inputs" and "imports that promote legacy evidence" exclusions are replaced by W9's adoption and transition rules. The old→new texts are §16.2; W9's acceptance is conditional on G7-C's register entry. |
| P-028 | Applied: token counts use the versioned W3 reference tokenizer; counts from different tokenizers are not combined (§14.2). |
| P-029 | Its two-family R3 rule is put to Stephen as W9-D3 (§11.2). |
| P-031, P-050, 06s §4 | The Gate 6 fresh SPEC-01 run is the system pilot evidence W9 consumes (§14.1). SCALE-01 is not a condition (06u D-2). |
| P-032 | Preserved: W11 governs Discovery objects; W9 sequences the legacy side. |
| P-034 | Preserved: consolidation by per-item transition. |
| P-042 | Governs dispatch: operator-mediated sessions; ARS never invokes a provider. P-033 is superseded (06g §2). |
| P-047 | Gate 9 owns RM-04's manuscript-review pilot (§12). |
| P-058, P-061 | Inputs (known limits; the SPEC-01 continuation), not W9 scope (§3.3). |
| D-G5-1(a) | Still restricts M/H model-graded acceptance. |
| W11 r0.5 | **Accepted** (D-G6-4 limb 1, Stephen, 2026-08-01; Jira KAN-19 comment 10358; blob `f90729d0`). Its strict catalogue was accepted (KAN-84; `research_system/discovery/accepted_w11.py`, catalogue blob `8d588185` at `09be63a9`) and genesis-imported into `TDL-ARS-G6-Control` (P-058, Step 3 batch 1). The durable acceptance record sits on unmerged commit `cee20209`; a separate task is landing it on main. |
| Route (ii) | **Stephen, 2026-10-22:** "Route (ii): a W9-owned closed schema family reusing W11's observation-inventory-mapping-transition pattern, with a lighter closed_reference observation path." |

Bounded assumptions:

- **W9-A1 — no runtime.** No handler implements W11's legacy rows OR-122 to OR-139 on `3fa437a1`. Their W11 schemas
  are materialized and accepted, but W9 does not use them (§5). Every W9 operation therefore waits on an
  implementation plan for the W9 family, outside this document.
- **W9-A2 — W7.** W7 (provider adapters and parity) is consumed only through P-042: operator-mediated sessions, no
  ARS provider invocation, no parity evidence required for Gate 7 dispatch (W9-D2).

### 2.2 Direct evidence inputs

| Evidence | Use in W9 |
|---|---|
| The W0 manifest (2026-06-28), addendum (2026-06-29), the accepted post-terminal addendum (`1ebcf96f`) and its acceptance record | Classes (manifest §4), source precedence (§8.4), import policy (§12), no-migration set (§10; G7-A §12), the re-derived Stage 1 classes (G7-A §6.1), Stage 2 (§9), post-freeze writers (§11), the A-001 list (§10) |
| `docs/plans/strategy/P01-Claim-Trace-Audit-2026-07-17.md` | Per-file draft verdicts; citable-artifact list (§3.2); holes |
| `docs/plans/strategy/P01-Adversarial-Mathematical-Review-2026-07-18.md` (#132) | A1–A4; the "no rung-4/5 claim promotion before A1 and calibration" condition |
| `docs/plans/strategy/APM-Failure-Inventory-to-ARS-Invariants-2026-07-17.md` | I1a–I11a; the self-attestation, silent-absence and no-revalidation classes |
| `results/trajectory_tda_integration/stage1/SUPERSEDED.md`; `w2_fallback_audit_2026-07-14.json` | Field-family supersession; the lines 69–71 conflict |
| W2 §§14, 22; W11 §§3, 7, 8; the accepted W11 schemas under `.research-system/schemas/contracts/w11/` | The pattern W9 copies, and the schemas it cannot reuse (§5.1) |
| W6 catalogue, 06a, 06b; 05-plan §4.4 | The `pilot_promotion` fixture set (§12.3) |
| 06l; 06u; handoff 07; 02-roadmap §4 and W9 entry; 04-plan §§2, 5–7; master plan §8 Phase F and §10 | Steps 0–7; scope; required contents; pilot rubric; stop rules; adoption |

### 2.3 Boundaries and consumers

| Boundary | W9 rule | Consumer |
|---|---|---|
| W2 control plane | Sole mutation boundary; the W9 family adds commands only through a reviewed implementation plan | Implementation plan |
| W11 | Unchanged. W9 copies its DAG pattern under separate schema IDs and catalogue | Portfolio Steward |
| W5 | Owns claim candidates and promotion; W9's adoption decision governs only whether legacy evidence is admissible to W5 (§9) | Assurance engine |
| W6 | Owns `pilot_promotion` and its fixtures (§12.3) | Eval runner |
| W3 | Owns context packets and the reference tokenizer (§14.2) | Context compiler |
| W8 | Owns grants for successor compute (§10) | Operator |
| Legacy surfaces | Read-only until an item's accepted transition | Humans; migration authority |

### 2.4 Design-entry-criteria disposition

| README criterion | Draft 0.2 disposition |
|---|---|
| 1. Decisions accepted or assumptions explicit | §2.1; W9-A1, W9-A2; owner decisions W9-D1 to W9-D14 open (§16) |
| 2. Evidence register | **Not yet.** `01-current-system-evidence.md` needs a dated W9 addendum before acceptance (W9-D8a) |
| 3. Boundaries and consumers | §2.3 |
| 4. Independent review owner | Assigned; the draft 0.1 review is on record; draft 0.2 goes to a focused re-review |
| 5. Acceptance tests before implementation | §17 |

## 3. Scope

### 3.1 Legacy surfaces

Registration is per exact file, never by glob (§4). The surfaces:

| Surface | What is registered | Ownership mode |
|---|---|---|
| Legacy research results | The exact result files named in the W0 manifest §5.2, G7-A §6 and audit §3.2, plus their supersession manifests and pre-registrations | `legacy_owned` |
| Legacy-bound contracts | The exact contracts whose binding tests read a registered legacy result, and the legacy input-provenance manifests (`t128-inputs.yaml`, `t138-w2-gap-closure-inputs.yaml`, `b9-om-gmm-inputs.yaml` and the others the inventory finds) | `legacy_owned`, role `shared_enforcement_surface` where ARS packs also bind them (§4.3) |
| Decision record | Legacy entries in the vault Computational-Log; `CONVENTIONS.md` locks | §7.3 exception |
| Coordination | `.apm/spec.md`, `.apm/plan.md`, `.apm/tracker.md` and the other tracked `.apm/` files; the untracked `.apm/memory/stage-NN/` logs and `.apm/bus/` files | `legacy_owned` |
| Manuscripts | `papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/` as whole roots; `papers/shared/` | `legacy_owned` |
| Retained branches | `paper/p01a-dedup-rewrite`, `pipe/two-machine-check`, and the others G7-A §12 lists | `legacy_owned` |
| Discovery | Vault `00-Meta/Discovery/_backlog.md` | `legacy_owned`; W11 governs (§15) |

**Not registered as legacy:** ARS-owned contracts and packs (for example #334's
`process-invariants/retired-plan-imperatives-quoted.yaml`), ARS planning documents, and every successor result.
Successor results are written only under the **successor results root** `results/ars/` (proposed, W9-D14), which is
disjoint from every registered legacy file.

### 3.2 Other legacy papers

P04 and the other result families under `results/` (poverty, financial) are legacy too: the APM freeze covered P04's
prose. They are not Gate 7's first subjects. W9-D13 proposes they stay `legacy_owned`, unregistered, until their own
intake.

### 3.3 Out of scope

- Implementing any schema, command, guard or projector.
- Deciding research questions the intake manifest carries (A1 fork, H3, A2 construction, Stage 2 scope).
- Manuscript authoring; provider invocation (P-042).
- The SPEC-01 continuation (P-061), which is ARS-native. If its R4 step consumes a frozen P01 representation, that
  representation enters only through §9 adoption and §10's input rule.

## 4. Path and writer registry (KAN-26)

### 4.1 Writers observed after the freeze (G7-A §11)

| Writer | Example | Effect |
|---|---|---|
| Repo-wide tooling through a reviewed PR | #277: three `papers/` files | Formatting, F401, one E741 rename; behaviour-preserving (reviewer-verified) |
| Session Working Note through a reviewed PR | #368: `.apm/tracker.md` | Appended note; no Task row edited |
| Owner-ruled result commit after the freeze merge | `1af52f6d` (H6) | Explicit User ruling |
| ARS-lane contract work through reviewed PRs | #168, #169 (WP6.3): activated `null-operation-changes-ph-input` and `markov-order-provenance`, added `markov-order-provenance-json-validation`, edited `monte-carlo-permutation-p-value` and `research-assurance.yaml` | Changed the enforcement state of contracts legacy results are read under |
| ARS planning contract through a reviewed PR | #334: added `retired-plan-imperatives-quoted.yaml` | ARS-owned; not a legacy file |
| **Direct push to main, no PR** | `5df0c001` (seven result files), `811d5a2b` (three input-provenance manifests) | Line endings and manifest rewrites; restored by #219; net nil |

### 4.2 Writer rule for a registered legacy file

1. **Allowed:**
   - (a) a legacy-lane commit the freeze permits (none while the freeze stands);
   - (b) a repository-wide change, **only with** Stephen's attributed note naming every registered file it touches
     with old and new blobs, plus an independent semantic-equivalence review of those files. The writer's own note
     does not qualify;
   - (c) an explicit owner ruling recorded in the decision log.
2. **Prohibited:** any successor writer; any unreviewed write, including a direct push with no PR; any write during
   an open observation or transition window (§8.3).
3. **Re-observation:** any blob change to a registered file, however it was allowed, re-triggers its observation and
   blocks every open observation, adoption or transition that binds the old blob.

### 4.3 Shared enforcement surfaces

A contract that both a legacy result and an ARS pack bind is registered with role `shared_enforcement_surface`. Its
writer set is ARS reviewed PRs **plus** the §4.2(b) owner note naming the legacy results the change affects. Each
change re-triggers observation of those results' enforcement state. W9-D14 asks Stephen to accept this split, or to
make every such contract ARS-owned with legacy results observed against a frozen copy.

### 4.4 Detection (W9-D5)

| Detector | Sees | Negative control (must fire) |
|---|---|---|
| Server-side branch protection on `main`: no direct pushes | Pushes | A direct push attempt is refused (owner-run check, not a destructive probe) |
| Post-merge first-parent detector over `origin/main` | Any commit touching a registered legacy file without a §4.2 record | Replays of `5df0c001` and `811d5a2b` against the registry are flagged |
| Vault append-only detector for the Computational-Log | An edit to any legacy entry's bytes (§7.3) | A fixture edit inside a legacy entry is flagged |

A client-side pre-commit hook is defence in depth only; it cannot see a push of a commit made elsewhere. None of
these is built here; each is a requirement on the implementation plan, with its negative control watched to fail
before the first registration.

### 4.5 Preparation, transition, cutover and retirement matrix

| Class of action | Allowed now | Required before it |
|---|---|---|
| Preparation: documents, read-only observation by a non-author session with Stephen's authorization, inventory design, membership tables, templates | Yes | — |
| Closed-reference observation and batch acceptance (§8.1) | No | Gate 7 opened (D-1 bar); G7-A, G7-B, G7-C accepted; the W9 catalogue accepted and imported (W9-D10); the §4.4 detectors live; Stephen's W0-D1 signature on all eight §14 items |
| Adoption (§9) | No | The item's closed-reference acceptance; Stephen's `AdoptLegacyAuthority` decision |
| Successor transition of a paper root (§8.2) | No | All of the above; the integration-pilot batch passed (§14.3); W0-D2 Stage 2 scope for its rows; the A-001 items feeding its claims resolved or scoped out; its `pilot_promotion` evidence (§12.3); W9-D7 manuscript route; Stephen's batch approval (D-G6-4 limb 2) |
| Whole-path cutover | No | Every item on the path transitioned; writer revocation; final observation; closure; Stephen's cutover Decision |
| Retirement | No | Durable cutover; no live authority reference; Stephen's retirement decision |
| Discovery items at 06l Step 3 or later | No | W0-D4's condition (§15) |
| **Explicitly prohibited before their gates:** migration of any item; mutation of a registered path; writer retirement; OR-032/OR-033; provider calls; research execution; eligibility change; claim promotion | No | Their own gates |

KAN-26's original transition bar ("Gate 6 pilot-promotion evidence") is superseded by D-1 (06u §12).

## 5. The W9 legacy schema family

### 5.1 Why not W11's schemas

W11's accepted schemas are closed (`additionalProperties: false`) and Discovery-specific:

- `path-registration-content` takes `vault_root_id` and a closed `role` enum of four vault roles;
- `legacy-record-observed` has no Git commit or blob, no W0 class, no importer identity and no conflict list;
- `legacy-transition-mapping-content` requires `target_object_refs` with at least one W11 portfolio object;
- W11 selectors are byte ranges, which cannot separate interleaved JSON keys;
- W11 §8.1: any name outside the closed sets needs a new reviewed W11 revision, and the genesis import is one-time.

W9 therefore defines its own family under `ars://legacy/`. It copies W11's ordering rules (no reverse edge;
observation before inventory before mapping before transition; independent observer and reviewer; Stephen-only
resolution) and W11 §7.3's handle-bound read protocol, extended to repository files.

### 5.2 Records

All records are strict, closed, immutable W2 objects.

| Record | Purpose | Key fields |
|---|---|---|
| `legacy-repository-path-registration` | Registers one exact legacy file | repository root ID; normalized path; resolved physical identity; source identity kind (`git_tracked` or `untracked_file` or `vault_file`); role (`legacy_research_result`, `legacy_supersession_manifest`, `legacy_pre_registration`, `legacy_contract`, `shared_enforcement_surface`, `legacy_coordination`, `legacy_task_log`, `legacy_bus_file`, `legacy_manuscript_root`, `legacy_decision_log_entry`, `conventions_lock`); ownership mode; writer classes (§4.2); prohibited consumers |
| `legacy-field-family-membership` | For one file schema, assigns every JSON pointer to exactly one named family, or to `unassigned`, which blocks import | file schema ID; family names; pointer → family map; author identity (independent of the importer); review ref |
| `legacy-observation` | One handle-bound observation of one registered file | registration ref; source identity (Git commit and blob, or handle-bound SHA-256 plus a dated frozen copy for untracked and vault files, with "no Git identity" as a recorded non-inference); importer identity and version; per-family W0 class with the **signed** W0 revision and signature record; typed qualifiers (§6.4); conflicts; non-inferences |
| `legacy-closed-reference-acceptance` | Light path: accepts a batch of observations as `closed_reference` | observation refs; independent review ref; Stephen's batch Decision |
| `legacy-adoption-decision` | §9 | observation and family refs; intended successor use; W5 admissibility consequence; qualifiers that must be discharged; Stephen's Decision |
| `legacy-discharge-relation` | A successor result discharges a legacy open item (an A-001 item or a hole) | successor result ref; legacy item ref; reviewer ref; Stephen's Decision under W0-D1 |
| `legacy-source-inventory`, `legacy-transition-mapping`, `legacy-ownership-transitioned` | Full path for `successor_owned` (§8.2) | As W11 §7.5–7.6, with W9 identities and a W11 `paper` object as the mapping target |
| `legacy-record-supersession` | Corrects an erroneous accepted observation or mapping | superseded record; replacing record; reason; reviewer; Stephen's Decision. The old record and its events stay; current use re-points (§13.2) |

### 5.3 The catalogue

The family is a separate W9 catalogue with its own exact Git/blob/SHA-256 identities, independently reviewed and
accepted by Stephen, then imported into the store by its own one-time W9 genesis transaction. W11's genesis is not
reused or repeated. W9-D10 asks Stephen to accept this route; the catalogue and its genesis row are written by the
implementation plan, not here.

## 6. Status mapping

### 6.1 Class to treatment

| W0 class | Permitted treatment |
|---|---|
| `authoritative` | Eligible for `closed_reference`. Usable by a successor only after adoption (§9). |
| `authoritative`, qualified | As above, with the qualifier carried (for example T1.2g/T1.7: "the dedup amendment may not be justified by the H₁ W₂ flip"; T1.9b: H7). |
| `authoritative_supersession` | `closed_reference` as a supersession relation. |
| `merged_draft` | Stays `legacy_owned` until its paper root transitions (§12); carries the audit's per-file verdicts as qualifiers. |
| `prepared`, `active` | Stay `legacy_owned` (none exist at `3fa437a1`). |
| `blocked` | Stays `legacy_owned`; the blocker is observed. |
| `deferred` (parked for ARS) | The legacy row may become `closed_reference`; the work re-enters only as a new successor Task (§10). |
| `superseded` | `closed_reference` with lineage; never current. |
| `stale_projection` | Observation only; the stronger record governs. |
| `unverified` | `closed_reference` with an `unverified` qualifier; adoption needs the evidence the class names. |

### 6.2 Field families

Families are addressed by `legacy-field-family-membership`: a JSON-pointer set per family for each file schema,
authored and reviewed independently of the importer. Every key in the file is assigned, including unprefixed keys
such as `t_ratio`, `d_perm` or `pvalue_null_draws`; an unassigned key blocks import. The families G7-A §6.1 names:

| Object | Families and classes |
|---|---|
| `usoc_headline_frozen_2026-05-28.json`, `bhps_headline_frozen_2026-05-28.json` (T1.37) | H₀ W₂ and landscape L² `authoritative`; H₁ W₂ `superseded` by the 2026-07-14 corrected files |
| `lm_sensitivity_L2500/L8000_frozen_2026-05-28.json` (T1.37) | H₀ `authoritative`; H₁ W₂ `unverified`; design-choice role stands |
| `stratified_markov1_W2_L5000_frozen_2026-05-29.json` (T1.3) | H₀ W₂ and landscape L² `authoritative`; H₁ W₂ `unverified`; Outcome A rests on H₀ alone |
| `bhps_nonoverlap_reanalysis_2026-06-09.json` (T1.26b) | Landscape `authoritative`; H₁ W₂ `superseded` (falsified 2026-07-16) |
| Markov-2 α=1 cell JSONs (H6) | Landscape L² `authoritative`; W₂ do-not-cite |
| `markov2_alpha_sweep_summary_2026-06-16.json` (T1.8) | W₂ `unverified` |
| Dedup comparison files (T1.2g, T1.7) | H₁ W₂ cell and decision counts from the 2026-07-14 corrected file; landscape, provenance and probes from the 2026-06-01 file |

### 6.3 Source precedence

W0 manifest §8.4, verbatim:

1. governing pre-registration/decision plus committed result and contract evidence;
2. current code and binding tests;
3. Manager review and accepted commit ancestry;
4. task-specific log/report;
5. Tracker and memory summary;
6. paper dashboard;
7. historical narrative.

`SUPERSEDED.md` lines 69–71 call the Markov-2 summary "presumed IMMUNE"; the T1.38 Phase 1 `[RESULT]` and
`w2_gap_closure_phase1_2026-07-16.json` record UNVERIFIABLE (G7-A §8). The observation of lines 69–71 is recorded
as a `stale_projection` with the conflict naming both records, and the summary's W₂ family takes `unverified`. The
import **resolves** by precedence; it does not block, because tier 1 settles it. The legacy file is not edited.

### 6.4 Qualifiers and corrections

Typed qualifiers carried on observations:

| Qualifier | Meaning | Example |
|---|---|---|
| `open_review_finding` | A recorded finding that affects the family's inferential reading | A1, A2, A3, A4 on every Markov-rung p-value family (G7-A §6.1, §7) |
| `audit_verdict` | A claim-trace audit verdict on a draft file | "entire file invalid" |
| `stale_projection_of` | The record contradicts a stronger one | Tracker row T2.24 |
| `corrected_by` | A dated correction entry supersedes part of the record | The 2026-07-11 T1.20 `[DECISION]`'s Tier 1 values, corrected 2026-10-22 (G7-A H10) |

`corrected_by` is a general typed relation, not a named instance. Imported values always come from the canonical
source by precedence: for H10 that is `tier1_clustered_firth_2026-05-16.json`, not the correction entry's prose.

## 7. Compatibility views

### 7.1 `.apm/`

The APM lane is frozen, and no unmodified APM Worker is active. W9 defines no `.apm/` compatibility writer; the W2
§14.3 namespace stays reserved and unregistered. A reactivated APM Worker's task stays `legacy_owned` (P-021).

### 7.2 Read-only legacy projection

A read-only projection of accepted observations may be published under a registered ARS namespace (W9-D8b). It
carries source position, projector version, content hash and rebuild identity, and is never an authority input.

### 7.3 The shared-writer exception (W9-D9)

The vault Computational-Log and `CONVENTIONS.md` have legacy and successor writers by design. W9 proposes a bounded
exception to 06l §4 and W11 §7.1 for these two files only:

1. **Selector:** a legacy entry is addressed by a heading-anchored entry hash (the exact bytes from its heading to
   its separator). The containing file's hash is recorded but is not required to stay stable, because new entries
   are prepended.
2. **Rule:** successor sessions only prepend new entries or add new locks. No byte inside a legacy entry or lock
   changes. Corrections are new dated entries linked by `corrected_by`.
3. **Window:** the entry hash, not the file, must be stable through an observation window.
4. **Detection:** the vault append-only detector (§4.4).
5. **Alternative:** legacy entries transition only from a frozen, dated export of the file, never from the live
   file.

`CONVENTIONS.md` is repository-canonical and reached from the vault by a symlink. It is registered at its repository
path only; the vault alias is a prohibited read path for observations.

## 8. Observation and transition

### 8.1 Light path: closed reference

For an item that only ever becomes `closed_reference`:

1. A non-author observer takes a handle-bound `legacy-observation`.
2. An independent reviewer checks the observation, its families and qualifiers against the signed W0 record.
3. Stephen accepts a batch by `legacy-closed-reference-acceptance`.

There is no inventory or mapping DAG on this path, and no successor object is created. A closed-reference item is
not usable by a successor until adopted (§9).

### 8.2 Full path: successor owned

For a paper root becoming `successor_owned`, W9 uses W11's DAG pattern with W9 identities: observation → accepted
source inventory of the root → accepted mapping to a W11 `paper` object → `legacy-ownership-transitioned`. Allowed
transitions: `legacy_owned → successor_owned`, `legacy_owned → closed_reference`,
`successor_owned → closed_reference`.

### 8.3 Windows

From observation to acceptance (light path) or transition (full path), the registered file's blob or, under §7.3,
its entry hash must not change. A change aborts with no event and re-triggers observation (§4.2 item 3).

### 8.4 Item granularity and targets

| Legacy item | Path | Target |
|---|---|---|
| Result file | Light | `closed_reference`; no successor object |
| Pre-registration, contract, supersession entry | Light | `closed_reference` |
| Legacy decision entry | Light, under §7.3 | `closed_reference` |
| Tracker row, task log | Light | `closed_reference` |
| Bus file | Not imported (§7.4 of the deprecation path, §13.3) | — |
| Parked computation's tracker row | Light | `closed_reference`; the work re-enters as a new successor Task (§10) |
| Paper root | Full | `successor_owned` W11 `paper` object |
| `papers/shared/` | Light, after both paper roots transition | `closed_reference` |

### 8.5 Preconditions per item

1. §4.5's column for its class;
2. Stephen's W0-D1 signature on all eight manifest §14 items, recorded in the observation;
3. its families assigned by an accepted membership table (§6.2);
4. for any item whose acceptance changes citability or feeds a claim, its `pilot_promotion` evidence (§12.3);
5. an independent review, and Stephen's decision; the producing actor cannot establish its own independence.

### 8.6 Actor roles

W11's owner rows name a "Gate 6 Manager" as requester and proposer (for example OR-130, OR-132). No APM Manager
exists under the freeze. In the W9 family these roles are: **requester and proposer** — the migration analyst, a
distinct ARS actor; **observer and reviewer** — independent ARS actors on a different session from the analyst;
**resolver** — Stephen.

## 9. Adoption (`AdoptLegacyAuthority`; W9-D11)

W2 §22.2 and W11 §2.3 assign selective legacy adoption to W9. Adoption is the only route by which legacy evidence
becomes usable by a successor object.

1. **Subject:** one accepted `closed_reference` observation, by family.
2. **Binding:** the exact observation, its families, signed W0 class, qualifiers, and the intended successor use
   (for example "input to T1.41 successor Task" or "evidence for claim candidate X").
3. **Resolution:** Stephen only (P-005: "upgrading imported evidence from provisional to authoritative").
4. **W5 consequence:** an adopted family is admissible to W5 for the named use only. Open `open_review_finding`
   qualifiers stay attached, and W5 cannot promote a claim resting on a family whose qualifier blocks it (for
   example A1–A3 on a rung-4/5 p-value, until the A1 fork is decided and the calibration runs).
5. **Revalidation:** any re-observation of the source (§4.2 item 3), any new qualifier, or any supersession (§13.2)
   suspends the adoption until re-resolved.

`legacy-discharge-relation` is the converse: it lets a successor result close a legacy open item. A successor
T1.41 result discharges A-001 item 1 only through a discharge relation that an independent reviewer checks and
Stephen resolves under W0-D1.

## 10. Parked legacy compute (W9-D1)

T1.41 and the Markov-2 α=1 recompute run, if authorized, as **new successor-owned ARS Tasks**:

1. **Legacy rows** move to `closed_reference` by the light path. No legacy Task is reopened.
2. **Pre-registration:** each Task files a **new** pre-registration in the vault, before dispatch. It cites the
   legacy pre-registration (the 2026-07-17 Markov-2 entry, or the 2026-07-16 double-null `[DECISION]` for T1.41) by
   identity and carries any change as its own content. For the Markov-2 recompute that includes the review finding
   A1 amendment; for T1.41, a design that answers A3 and may answer A1 and A2. Stephen resolves it (P-005). The
   legacy record is not edited.
3. **Inputs:** regenerated inside the successor Task from committed scripts at a pinned commit (for T1.41,
   `scratch/w2_fallback_audit/w2_gap_closure_table1_h1.py`, 06u §6.1), or referenced by content hash only. Restricted
   or UKDA-derived bytes (null caches, embeddings, `*.csv`, `*.pkl`) never enter the ARS artefact store; they stay
   under `PROJ_ROOT`, gitignored, and are referenced by hash and path. Legacy embeddings that a successor Task uses
   are adopted first (§9).
4. **Outputs:** under `results/ars/` only (§3.1).
5. **Precondition:** the G7-A §17 trigger fires on dispatch, so a dated W0 addendum is due; the dispatch record
   cites it.
6. **Dispatch model:** §11.

**Alternative rejected:** transitioning each paper first and running the compute in its successor scope. That
delays the calibration every rung-4/5 claim needs (A3) behind the manuscript route (§12).

## 11. Dispatch model

### 11.1 First release (W9-D2)

Gate 7 dispatch is operator-mediated under P-042, as Gate 6's was. No live-provider reactivation follows, and W7
parity evidence is not required for Gate 7 dispatch.

### 11.2 Model-family coverage (W9-D3, re-framed)

The question is whether P-029's two-family rule survives P-042's amendment of P-029's "provider-runtime portions",
for operator-mediated sessions.

- **If it survives (recommended):** it applies **at dispatch** to every item in P-005's R3 set (pre-registration
  changes, R3 dispatch, decision reversal, claim promotion, adoption), with verifier-route availability proven
  before any compute: the operator names the second-family session (for example Codex) in the dispatch record.
  Without it, the item records `r3_family_coverage_insufficient` and does not dispatch.
- **If it does not:** each item records one-family review as an accepted known limit in its own decision, never as
  a precedent. Gate 6's one-family reviews were a P-058 known limit, not a precedent.

## 12. Manuscripts and pilot-promotion evidence

### 12.1 Papers transition last, as whole roots (W9-D6)

A paper root transitions only after the integration-pilot batch has passed (§14.3), and only when:

- every A-001 item feeding one of its claims is discharged (§9) or scoped out by Stephen;
- W0-D2's Stage 2 decision covers its rows;
- the audit verdicts and the §6.2 HOLD are carried as qualifiers;
- for any rung-4/5 claim it keeps, the A1 fork is decided and the calibration has run.

### 12.2 Manuscript review (W9-D7)

P-047 places manuscript review at Gate 9. Prose waits for that capability. Compute (§10) and closed-reference
imports (§8.1) may proceed first.

### 12.3 The `pilot_promotion` set (06u D-1)

The set is derived from the owning catalogue, not chosen per item. Source: the 05-plan §4.4 deferred list, 06a and
06b. Every member is assigned:

| Fixture | Assignment for Gate 7 items |
|---|---|
| F-006 stale paper dashboard | Paper-root transitions |
| F-015 sanity-value anchoring | Adoption of any statistical family |
| F-016 conceptual direction catch | Successor compute (§10) |
| F-017 missing comparison fields | Closed-reference acceptance of sensitivity and comparison files |
| F-018 superseded-but-live provenance | Every result-family observation |
| F-019 result-to-claim overreach | Paper-root transitions; adoption for a claim |
| F-023 ambiguous human approval | Every import (status words never become P-005 decisions) |
| F-024 qualitative artefact lifecycle | **Exclusion proposed:** no qualitative legacy artefact in P01 |
| F-029 safe-distractor invariance | Successor compute context packets; the §14.2 recall metric |
| F-030 addendum lineage and cumulative budget | Successor compute context packets |
| F-037 Partial/negative/superseded/claim separation | Every result-family observation; paper-root transitions |
| F-038 domain-pack applicability | Any item using the TDA pack's lanes |
| S-005 comparative conflict | Items where two results compete for one object (for example the T1.3 source and the 2026-05-13 battery) |
| S-007 stale review hash | Every review |
| S-014 backup, restore, machine move | Materialized in the `foundation_release` tranche (05b); re-run after each W9 batch |
| S-015 supersession cycle | Every `legacy-record-supersession` |
| S-016 R3 provider outage | **Re-specified under P-042** (W9-D12b): an operator-mediated second-family session is unavailable → `r3_family_coverage_insufficient`; its `unable_to_grade` H row stays |

Per-item applicability is proposed by the item's independent reviewer and fixed by Stephen in the batch decision,
never by the item's producer. An exclusion (F-024, S-016's H row) is an owner-accepted record.

## 13. Rollback, recovery and deprecation

### 13.1 Rollback (W9-D4)

- **Before commit:** any stop leaves the item `legacy_owned`; no event; no change to the legacy file.
- **After commit, closed-reference item:** the accepted record is superseded by `legacy-record-supersession`
  (§13.2); the old record and its events stay.
- **After commit, paper root:** recovery creates a **new successor paper object** that cites the transitioned paper
  by lineage and resumes under successor authority, or Stephen declares a **manual-operation mode** naming one human
  writer for the successor paper root (04-plan §7: "return the greenfield paper to manual operation"). Authority
  never returns to `legacy_owned` or to APM.
- **In every case** no accepted research artefact, result or decision changes.
- **06l's "tested rollback handle"** becomes, for each item: the pre-commit abort path and, after commit, the
  named supersession or recovery route, each exercised once on a scratch store before the item's batch.
- G7-C carries old→new text for 06l Steps 5, 6 and 7 (§16.2).

### 13.2 Supersession of an erroneous record

An accepted observation, closed-reference acceptance, adoption or mapping found wrong is superseded by a new record
with reason, reviewer and Stephen's Decision. Current use re-points to the new record. Adoptions that relied on the
old record are suspended (§9 item 5). Supersession cycles are rejected (S-015).

### 13.3 Deprecation path for the bus and Tracker

1. **Freeze:** already in force (2026-07-18).
2. **Bus:** `.apm/bus/` files are gitignored, single-slot and overwrite-prone (W0 §8.2). They are **not imported**.
   One dated, handle-bound inventory of the directory (names, sizes, SHA-256) is taken as a closure record, so their
   absence from import is a recorded decision, not silence.
3. **Tracker and logs:** each tracker row and task log is observed and accepted `closed_reference` by the light path.
4. **Writer revocation for `.apm/`:** sessions stop writing Working Notes to `.apm/tracker.md` (the #368 case);
   Stephen records the revocation; the §4.4 detector watches the path.
5. **Final observation and closure** of the whole `.apm/` set.
6. **Projection replacement:** the §7.2 legacy projection, if accepted.
7. **Retirement record** under 06l Step 7, by Stephen.

### 13.4 Stop criteria

Stop a transition, batch or pilot when any of these holds (04-plan §7 and W9-specific):

- a critical interface remains unspecified;
- a fixture in the item's §12.3 set fails or cannot be graded independently;
- recovery cannot prove the canonical tail and projected state;
- a legacy record would reach successor use without adoption, or a status word would stand in for evidence;
- a registered file would have two writers, or a §4.4 detector is absent or has not been watched to fail;
- a family cannot be addressed by the accepted membership table;
- a precedence conflict is unresolved;
- a review is not independent or is on a stale hash;
- §11.2's coverage is missing where it applies;
- a source changes in an observation or transition window;
- the integration pilot misses a pre-registered threshold (§14.3);
- operator burden makes routine bypass of a control likely.

## 14. Pilot rubric, baseline and metrics

### 14.1 The system pilot already run

The Gate 6 fresh SPEC-01 run (P-058) is the system pilot under P-031's amended occupant rule. Against 04-plan §6:

| Criterion | Gate 6 evidence | Status |
|---|---|---|
| Deterministic replay and recovery | Replay, backup, evidence-only restore, frozen-checkout replay | Met; same-disk only (P-050) |
| No silent overwrite or ambiguous authority | Append-only ledger | Met with P-058 known limits: the governing scientific-review record placed through the internal store; approve-only reviews whose findings live off the ledger |
| Complete provenance | Hash-pinned scripts; evidence index | Met with the same known limits; Task acceptance asserted criterion 5 before it could hold |
| Required scientific and operational graders | Independent reviews, approve-only, one model family; D-G5-1(a) | Partly met |
| Smaller context without reduced recall | Not measured | **Open** |
| Acceptable operator burden | Not measured | **Open** |
| Stephen's approval for R3 or claim transitions | Every owner point | Met |

### 14.2 Integration-pilot rubric (W9-D12)

The first W9 batch is the integration pilot. Following the roadmap §4 rubric, it:

- contains **closed-reference items only** (result files, decision entries, tracker rows): no paper root, no
  claim-bearing adoption, no successor compute;
- is bounded (proposed: at most 20 items) and drawn from families G7-A has already classified;
- has only successor-side, supersedable effects;
- avoids a large historical import, unresolved data access and any paper-claim reversal.

Papers come last, after this batch passes. Master plan Phase F says wider adoption needs Stephen's explicit
authorization and that "no conclusion about migrating the two APM papers follows automatically". W9-D12 asks
Stephen for that authorization as a separate decision before any paper-root transition, and proposes old→new text
for roadmap §4 and 04-plan §6 through G7-C (§16.2).

### 14.3 Metrics and thresholds

| Metric | Baseline | Measure |
|---|---|---|
| Governing-evidence recall | Per item, an independent reviewer compiles the governing-record set from G7-A §§4–10 and the audit; it is hashed and filed **before** the batch | Fraction of that set present in the ARS observation and review packet |
| Context size | The same set's size | Packet size in the versioned W3 reference tokenizer (P-028); one tokenizer for both |
| Operator burden | — | Owner actions and wall time per item, from the owner log |
| Cost | — | Owner minutes plus compute hours (P-042: no per-call provider cost) |
| Defects | — | Review findings per item by severity |
| Recovery | — | Replay and restore after the batch (S-014) |

**Thresholds** are filed by Stephen as a hashed, dated pre-registration in the vault before the batch's first
acceptance. A missed threshold stops further batches. It cannot reverse committed records; those are superseded only
through §13.2 if wrong.

## 15. Discovery boundary (W0-D4)

W0-D4: no Discovery item takes a 06l Step 3 or later action until G7-B's Discovery inventory is accepted.

**This section is not that inventory.** An inventory needs observed rows. W9-D8c proposes that, before W9's
acceptance, a **non-author session** with Stephen's authorization takes a dated, read-only observation of vault
`00-Meta/Discovery/_backlog.md`: full SHA-256, byte length, row count, and each active item with a row anchor. That
observation, reviewed independently and accepted by Stephen, is the G7-B Discovery inventory. Until it is accepted,
W0-D4's condition stays open, and G7-C records that.

Known from the record (for the observer to confirm, not as the inventory): the registered sheaf-Laplacian dispatch
and the MCbiF decision-pending battery (P-032); WT-2 and WT-3 (freeze handoff §3); the MCbiF batteries in the
Computational-Log (2026-07-16, labelled P01; 2026-07-18, labelled P04). The SPEC-01 Candidate `obj_a9ba6213-…` is
already successor-owned and is not a legacy item. P04's ownership mode is W9-D13.

The per-item transition of a Discovery item still uses W11's accepted machinery (W11 §7.5), once implemented.

## 16. Owner decisions and amendments

### 16.1 Decisions

| ID | Decision | Recommendation |
|---|---|---|
| W9-D1 | Parked compute (§10) | New successor Tasks; new pre-registrations citing the legacy ones; inputs regenerated or hash-referenced, never restricted bytes in the store; G7-A §17 addendum on dispatch |
| W9-D2 | First release (§11.1) | Operator-mediated under P-042; no provider reactivation |
| W9-D3 | Family coverage (§11.2) | The rule survives; at dispatch; over P-005's full R3 set |
| W9-D4 | Rollback and recovery (§13.1) | As §13.1, including the paper recovery route; G7-C amends 06l Steps 5–7 |
| W9-D5 | Detectors (§4.4) | Branch protection, a post-merge detector and a vault detector, each watched to fail before the first registration |
| W9-D6 | Paper granularity (§12.1) | Whole root, last |
| W9-D7 | Manuscript review (§12.2) | Wait for Gate 9 for prose |
| W9-D8a | Evidence register | A dated W9 addendum to `01-current-system-evidence.md` before acceptance |
| W9-D8b | Projection namespace (§7.2) | `.research-system/projections/legacy/`, registered under the W9 family |
| W9-D8c | Discovery observation (§15) | Yes: a non-author, read-only, dated observation before W9's acceptance |
| W9-D9 | Shared-writer exception (§7.3) | Accept, with the heading-anchored selector and the vault detector |
| W9-D10 | W9 catalogue and its own one-time genesis (§5.3) | Accept |
| W9-D11 | Adoption semantics (§9) | Accept `AdoptLegacyAuthority` as Stephen-only, use-scoped and revalidating |
| W9-D12a | Integration-pilot rubric and Phase F wider-adoption authorization (§14.2) | Accept the rubric; authorize wider adoption separately, after the pilot |
| W9-D12b | S-016 under P-042 and F-024's exclusion (§12.3) | Accept both |
| W9-D13 | P04 and other legacy result families (§3.2) | `legacy_owned`, unregistered until their own intake |
| W9-D14 | Shared enforcement surfaces and the successor results root (§3.1, §4.3) | Accept the `shared_enforcement_surface` split; `results/ars/` |

### 16.2 Amendments carried to G7-C (old→new texts)

| Source | Old | New (proposed) |
|---|---|---|
| P-026 legacy boundary | "the foundation cannot write, migrate, normalize, or promote their tasks, evidence, decisions, or claims" | "…except through W9's attributed observation, adoption and per-item transition, each resolved by Stephen; nothing is written to legacy files" |
| 04-plan §2 | "never migrated into the prototype and are never used as live pilot inputs" | "enter ARS only by W9 observation, adoption and per-item transition; legacy files are never written" |
| 04-plan §5 exclusion | "imports that promote legacy evidence into successor authority" | "imports that promote legacy evidence without a W9 adoption decision" |
| 04-plan §6, roadmap §4 | The first pilot is "the first paper initiated after the two current APM-managed papers" | "The system pilot was Gate 6's SPEC-01 run; the Gate 7 integration pilot follows W9 §14.2's rubric; wider adoption needs Stephen's separate authorization" |
| 06l Step 5 | "Rollback returns the item to its prior authority" | "Before commit, a stop leaves the item `legacy_owned`; after commit, recovery is successor-side (W9 §13.1)" |
| 06l Step 6 | "Roll back to the previous writer only through the recorded recovery procedure" | "Recovery is successor-side; legacy writers are never re-enabled (W9 §13.1, W11 §7.6.2)" |
| 06l Step 7 | "Retirement is reversible only by restoring the recorded prior surface" | "A retired surface is restored only as a read-only projection; authority does not return" |
| KAN-13 "additive 06i" | — | Resolves to 06l; 06i contains no Gate 7 text |

## 17. Acceptance-test families (specification only)

| ID | Invariant | Negative control |
|---|---|---|
| W9-T1 | A status word never yields acceptance | Observe a `Done` tracker row; no acceptance or adoption |
| W9-T2 | Families survive import | Observe T1.37's headline; H₁ W₂ is `superseded` |
| W9-T3 | Every key is in exactly one family | A file with an unassigned key; import blocks |
| W9-T4 | Precedence resolves lines 69–71 | Import them alone; the summary's W₂ family is `unverified`, not "IMMUNE" |
| W9-T5 | No return to `legacy_owned` | Submit `successor_owned → legacy_owned`; rejected |
| W9-T6 | A change in a window aborts | Change the blob (or a legacy entry hash) after observation; no event |
| W9-T7 | Detectors fire | Replay `5df0c001` and `811d5a2b`; edit a legacy log entry; each flagged |
| W9-T8 | No successor use without adoption | Reference an unadopted closed-reference family in a successor Task; rejected |
| W9-T9 | Adoption revalidates | Re-observe an adopted source with a new blob; the adoption suspends |
| W9-T10 | Parked compute writes nothing legacy | A successor Task writing a legacy path or legacy pre-registration; rejected |
| W9-T11 | Restricted bytes stay out of the store | Register a `*.pkl` or null cache as an ARS artefact; rejected |
| W9-T12 | Family coverage at dispatch | Dispatch an R3 item with no second-family session named; blocked before compute |
| W9-T13 | Corrections bind generally | Import any decision entry with a `corrected_by` relation; values come from the canonical source |
| W9-T14 | Supersession is acyclic and keeps history | Supersede a record twice in a cycle; rejected; old events intact |
| W9-T15 | Paper recovery changes no accepted artefact | Recover a transitioned paper; every legacy blob unchanged |
| W9-T16 | Thresholds precede the batch | A threshold record dated after the batch's first acceptance; the batch is invalid |

## 18. Independent review and exit gate

- [x] Independent adversarial review of draft 0.1 (REWORK REQUIRED; `b7fd4415`).
- [ ] Author reconciliation of every finding (draft 0.2; the reconciliation record).
- [ ] Focused independent re-review of draft 0.2.
- [ ] Stephen's decisions W9-D1 to W9-D14.
- [ ] The §15 Discovery observation, if W9-D8c is accepted.
- [ ] The evidence-register addendum (W9-D8a).
- [ ] Stephen's acceptance of the exact reconciled revision, conditional on G7-C's register entry (§16.2).

Acceptance of W9 opens nothing, transitions nothing and authorizes no implementation.
