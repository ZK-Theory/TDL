# W9 — Migration, Compatibility, and Pilot Specification

**Date:** 2026-10-22<br>
**Status:** `review_pending`; draft 0.4, reconciling the re-check of draft 0.3
(`reviews/g7b-w9-draft-0-3-re-check-e5432e44-2026-10-22.md`, REWORK REQUIRED (narrow)), after the reviews of drafts
0.1 and 0.2. Dispositions: `reviews/g7b-w9-reconciliation-2026-10-22.md`.<br>
**Specification version:** 0.4<br>
**Design authority:** accepted W1, W2, W3, W4, W5, W6, W7, W8 and W11 (revision 0.5, blob `f90729d0`, D-G6-4 limb 1,
2026-08-01); P-004, P-005, P-021, P-026, P-028, P-029, P-031, P-032, P-034, P-042, P-047, P-050, P-058, P-061; the
accepted 06u scope (D-1 to D-5); the accepted G7-A W0 post-terminal addendum (revision 3, blob `1ebcf96f`) and W0-D1
to W0-D4; Stephen's choice of schema route (ii) and of the W9-owned paper-root target, 2026-10-22 (§2.1)<br>
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
   decision (§9) binds it under P-005. "Citation by reference" is not a use, and neither is a paper root's
   transition: the result families a transitioned paper's drafts cite must be adopted or marked unadopted (§12.1).
2. **Three ownership modes, one writer, with two declared exceptions.** Every legacy item is exactly one of
   `legacy_owned`, `successor_owned` or `closed_reference` (P-004). A registered legacy file has one writer set. The
   Computational-Log and `CONVENTIONS.md` are the two files that cannot meet that rule today; they are handled by a
   bounded exception (§7.3, owner decision W9-D9).
3. **W9 owns its own closed schema family** (route (ii)). It reuses W11's observation → inventory → mapping →
   transition pattern, with its own registration root, selectors, target kinds and catalogue. It neither extends nor
   reopens W11, whose accepted catalogue was genesis-imported into the Gate 6 store.
4. **Two observation paths.** Items that only ever become `closed_reference` use a light path: a handle-bound
   observation, an independent review, and Stephen's batch decision (§8.1). Items that become `successor_owned` (the
   paper roots) use the full transition chain (§8.2), whose target is a W9-owned `legacy-paper-root` record. A later
   W11 dossier admission may reference that record; W9 never writes a W11 portfolio object.
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
| Paper-root target | **Stephen, 2026-10-22:** "For N-1, make the full-path target a W9-owned legacy-paper-root record that a later W11 dossier admission references." |

Bounded assumptions:

- **W9-A1 — no runtime.** No handler implements W11's legacy commands OR-031 to OR-033 or their authority rows
  OR-122 to OR-139 on `3fa437a1`. Their W11 schemas are materialized and accepted, but W9 does not use them (§5).
  Every W9 operation therefore waits on an implementation plan for the W9 family, outside this document.
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
| Manuscripts | `papers/P01-A-JRSSA/`, `papers/P01-B-JRSSB/` as whole roots; `papers/shared/` | `legacy_owned`. A root is the one directory registration W9 allows. As in W11 §7.2, it authorizes no nested file its inventory does not list; the root's full-path inventory lists every file under it |
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
writer set is ARS reviewed PRs **plus** a §4.2(b) owner note. The set of legacy results a change affects is derived
by the independent reviewer from the contract's binding tests, never named by the writer. Each change re-triggers
observation of those results' enforcement state. W9-D14 asks Stephen to accept this split, or to
make every such contract ARS-owned with legacy results observed against a frozen copy.

### 4.4 Detection (W9-D5)

| Detector | Sees | Negative control (must fire) |
|---|---|---|
| Server-side protection on `main` of `ZK-Theory/TDL`: the existing GitHub ruleset "P-049 Gate 6 main merge admission" (ID 20822054, `enforcement: active`, rules `pull_request`, `required_status_checks`, `merge_queue`, `non_fast_forward`), created 2026-08-13, after both direct pushes. Its bypass list is `RepositoryRole` 5 with `bypass_mode: pull_request`. Its `pull_request` rule has `required_approving_review_count: 0` and `require_code_owner_review: true`, so §4.2's "reviewed" is only partly enforced server-side; the §4.2 review record supplies the rest | Pushes outside a PR | This is a configuration, not a watched failure: its control is a recorded read of the ruleset and bypass list, re-read before each batch. Bypass use is seen through the ruleset's rule-suite history (`rulesets/rule-suites`), which the post-merge detector reads, because a first-parent walk cannot tell a bypassed merge from a normal one |
| Post-merge first-parent detector over `origin/main` | (1) Any commit touching a registered legacy file without a §4.2 record; (2) any change under `results/` outside the registered successor root `results/ars/` without a §4.2 record, so unregistered legacy families (W9-D13) are still guarded | Replays of `5df0c001` and `811d5a2b` are flagged; a fixture change to an unregistered file under `results/` is flagged |
| Vault detector for the Computational-Log | Any difference between a live legacy entry and the baseline export; a missing, renamed or duplicated legacy heading anchor; any unparseable heading (§7.3) | A fixture edit inside a legacy entry, and a renamed legacy heading, are each flagged |
| Repository check for `CONVENTIONS.md` | Any change to a legacy bullet or paragraph against the `4b143c92` blob; any change to a legacy section that is not a pure insertion of successor bullets (§7.3) | A modified legacy bullet is flagged; an inserted successor bullet in a legacy section is not |

A client-side pre-commit hook is defence in depth only; it cannot see a push of a commit made elsewhere. The
ruleset exists; the two detectors are requirements on the implementation plan. Each negative control is watched to
fail before the first registration.

### 4.5 Preparation, transition, cutover and retirement matrix

| Class of action | Allowed now | Required before it |
|---|---|---|
| Preparation: documents, read-only observation by a non-author session with Stephen's authorization, inventory design, membership tables, templates | Yes | — |
| Closed-reference observation and batch acceptance (§8.1) | No | Gate 7 opened (D-1 bar); G7-A, G7-B, G7-C accepted; the W9 catalogue accepted and imported (W9-D10); the §4.4 detectors live; Stephen's W0-D1 signature on all eight §14 items |
| Adoption (§9) | No | The item's closed-reference acceptance; Stephen's `AdoptLegacyAuthority` decision |
| Successor compute dispatch (§10; likely the first Gate 7 action, T1.41) | No | Gate 7 opened; the new pre-registration resolved by Stephen; §11.2 family coverage proven before compute; F-016, F-029 and F-030 evidence (§12.3); the W8 grant; adoption of any legacy input it uses (prefer regeneration); the dated W0 addendum for the dispatch accepted (G7-A §17) |
| Successor transition of a paper root (§8.2) | No | All of the above; the integration-pilot batch passed (§14.3); W0-D2 Stage 2 scope for its rows; the A-001 items feeding its claims resolved or scoped out; every cited result family adopted or marked unadopted (§12.1); its `pilot_promotion` evidence (§12.3); W9-D7 manuscript route; Stephen's batch approval (D-G6-4 limb 2). The target is a W9 `legacy-paper-root` record; a W11 `paper` object, if wanted, needs a separate W11 dossier admission (§8.2) |
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
| `legacy-path-registration` | Registers one exact legacy file | root kind and ID (`repository_root` or `vault_root`); normalized path; resolved physical identity; source identity kind (§5.4); role (`legacy_research_result`, `legacy_supersession_manifest`, `legacy_pre_registration`, `legacy_contract`, `shared_enforcement_surface`, `legacy_coordination`, `legacy_task_log`, `legacy_bus_file`, `legacy_manuscript_root`, `legacy_decision_log_entry`, `conventions_lock`, `successor_results_root`, `legacy_read_only_projection`); ownership mode; writer classes (§4.2); prohibited consumers |
| `legacy-field-family-membership` | For one file schema, assigns every JSON pointer to exactly one named family, or to `unassigned`, which blocks import | file schema ID; family names; pointer → family map; author identity (independent of the importer); review ref |
| `legacy-light-inventory` | For a registered Markdown or coordination file that will be closed or cut over, the complete list of its items | registration ref; source identity; selector kind (§5.5); one row per item with its selector and raw-row hash; blocker rows for every unparseable region, never omissions; an independent reproduction ref |
| `legacy-observation` | One handle-bound observation of one registered file, or of one item in it by a §5.5 selector | registration ref; selector (whole file, JSON-pointer family set, or §5.5 item selector) and the light-inventory row it binds, where one exists; source identity (§5.4); importer identity and version; per-family W0 class with the **signed** W0 revision and signature record; typed qualifiers (§6.4); conflicts; non-inferences |
| `legacy-closed-reference-acceptance` | Light path: accepts a batch of observations as `closed_reference` | observation refs; independent review ref; Stephen's batch Decision |
| `legacy-adoption-decision` | §9 | observation and family refs; intended successor use; W5 admissibility consequence; qualifiers that must be discharged; Stephen's Decision |
| `legacy-discharge-relation` | A successor result discharges a legacy open item (an A-001 item or a hole) | successor result ref; legacy item ref; reviewer ref; Stephen's Decision under W0-D1 |
| `legacy-paper-root` | The successor-owned target of a paper root's transition | paper key (P01-A, P01-B); manuscript root path; qualifier set; owner; for a recovery root only, the predecessor root by lineage and Stephen's recovery Decision (§13.1). **No transition ref and no citation status**: the link to the transition is projected from `legacy-ownership-transitioned`, which names the root, never the reverse. It is a W9 record, not a W11 portfolio object, and carries no programme, hypothesis, method, dataset or claim refs |
| `legacy-paper-citation-status` | The adopted or unadopted status of each result family a root's drafts cite (§12.1) | root ref; the frozen cited-family set's hash; per family: adopted (adoption ref) or unadopted. It points at the root, so the root is never revised; a later status supersedes an earlier one |
| `legacy-source-inventory`, `legacy-transition-mapping`, `legacy-ownership-transitioned` | Full path for `successor_owned` (§8.2) | As W11 §7.5–7.6, with W9 identities; the mapping target is a `legacy-paper-root` record |
| `legacy-record-supersession` | Corrects an erroneous accepted observation or mapping | superseded record; replacing record; reason; reviewer; Stephen's Decision. The old record and its events stay; current use re-points (§13.2) |

### 5.3 The catalogue

The family is a separate W9 catalogue with its own exact Git/blob/SHA-256 identities, independently reviewed and
accepted by Stephen. It enters a store as W11 §1 item 7 requires for W11's own catalogue:

1. **The store.** The implementation plan names the target store, and Stephen decides it. **The Gate 6 store
   `TDL-ARS-G6-Control` is not appended to**: it stays frozen at 91 events as Gate 6 evidence (P-058, step 6).
2. **A bootstrap contract.** A separately accepted, minimal W9 bootstrap contract imports the accepted W9 envelope
   through one independently verified genesis transaction. The W9 runtime cannot produce or accept its own
   prerequisite.
3. **A scoped grant.** The genesis runs under an owner grant scoped to the W9 catalogue stream, as Gate 6's W11
   genesis did (P-058, Step 3 batch 1).
4. **W11 in a new store.** A new store also needs the accepted W11 catalogue's own genesis before any W11-referencing
   record exists. W9 reads W11's genesis as one-time per store; the implementation plan confirms that reading with
   the W11 genesis code (`research_system/discovery/accepted_w11.py`) before relying on it.
5. **Protected identities.** New W2 commands for the W9 family change the 06h append-path census and the protected
   tree identities that P-059 re-accepted at exact bytes. The implementation plan carries that re-acceptance as an
   owner decision.

W9-D10 asks Stephen to accept this route. The catalogue, bootstrap contract and genesis row are written by the
implementation plan, not here.

### 5.4 Source identity kinds

| Kind | Identity | Frozen copy |
|---|---|---|
| `git_tracked` | Git commit and blob, plus SHA-256 of the bytes read | Not needed; Git holds the bytes |
| `untracked_file` | Handle-bound SHA-256, size and path; "no Git identity" recorded as a non-inference | A dated frozen copy in the ARS evidence store, for files that are not restricted |
| `restricted_untracked_file` | Handle-bound SHA-256, size and path only; "no Git identity" and "no frozen copy" recorded as non-inferences | **None in the ARS store.** Restricted or UKDA-derived bytes (null caches, embeddings, `*.csv`, `*.pkl`) stay under `PROJ_ROOT`, gitignored. Any frozen copy is kept there, outside the store, and referenced by hash. |
| `vault_file` | Handle-bound SHA-256, size and vault path | A dated frozen copy in the ARS evidence store |

Regeneration from committed scripts (§10) is preferred to observing and adopting a restricted file.

### 5.5 Item selectors

| File | Selector |
|---|---|
| JSON result | A JSON-pointer family set from the accepted `legacy-field-family-membership` (§6.2) |
| `.apm/tracker.md` task table | A task-ID-anchored row: the exact bytes of the table row whose first cell is the task ID, and its hash |
| `.apm/tracker.md` Working Notes | A date-heading-anchored entry: the bytes from the entry's bullet or heading to the next, and its hash |
| `.apm/memory/stage-NN/*.log.md` | The frontmatter block (between the opening and closing `---`), and its hash |
| Computational-Log | A heading-anchored entry, from the frozen baseline export (§7.3) |
| `CONVENTIONS.md` | A bullet or paragraph inside its section, from the `4b143c92` blob (§7.3); the trailing "Last updated" footer is structural bytes, not a lock |
| Any other Markdown file to be closed or cut over | A heading-anchored section, with a light inventory |

Any region of a file a light inventory covers that no selector addresses becomes a blocker row. A duplicate anchor
(two Working Notes under one date heading, two tracker rows with one task ID, two log entries with one heading) is
also a blocker row, never resolved by position.

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
exception to 06l §4's single-writer rule for these two files only. (W11 §7.1 governs only W11's Discovery vault
paths, which W9 does not use, so no W11 exception is sought.)

1. **The legacy set is decided by object, then date.** An entry or lock is **legacy** if it is about a
   `legacy_owned` object (P01-A or P01-B labels, T-numbered APM tasks, APM-lane locks) **and** dates from on or
   before the freeze (Computational-Log heading date on or before 2026-07-18; `CONVENTIONS.md` content committed
   before #126's merge, `4b143c92`). Entries and locks about ARS itself (P00 and other ARS-lane entries, the "ARS
   Foundation Governance" section's locks) are **successor** regardless of date; for example the 2026-07-16 "P00:
   Gate 5 production authority-bootstrap manifest approved" entry is successor. Successor corrections of legacy
   entries (for example the 2026-10-22 T1.20 correction) are successor entries. The baseline observer lists every
   entry and lock with its classification; an entry it cannot classify is a blocker, and Stephen accepts the list.
2. **Two baselines.**
   - **Computational-Log** (not under Git): a non-author observer takes a dated **baseline export** of every legacy
     entry as exact bytes, each with its heading-anchored hash, plus the export's own hash. The export lives in the
     repository under the W9 evidence area, so its hash is anchored in a Git commit before Stephen accepts it.
   - **`CONVENTIONS.md`** (under Git): the legacy baseline is the file's blob at `4b143c92`, selected at bullet or
     paragraph granularity (§5.5). No export is needed.
3. **Transitions read the baseline (the default).** Legacy entries are observed only from the frozen export, and
   legacy locks only from the `4b143c92` blob, never from the live files. There is no live-file window to hold.
4. **The live rule.**
   - Computational-Log: successor sessions only add new entries. No byte of a live legacy entry may differ from the
     export.
   - `CONVENTIONS.md`: every later change to a section that holds legacy locks must be a pure insertion of successor
     bullets or paragraphs. No legacy bullet or paragraph is modified or deleted. (Since #126, 117 successor lines
     have been inserted into the "ARS Foundation Governance" section; under the object rule that whole section is
     successor, and the rule applies to sections that hold legacy locks.)
   - Corrections are new dated successor entries linked by `corrected_by`, which later entries may themselves
     correct.
5. **Detection** (§4.4): the vault detector compares every live legacy entry with the export and flags missing,
   renamed or duplicated legacy anchors and unparseable headings; the repository check compares `CONVENTIONS.md`
   with the `4b143c92` blob under the insertion-only rule.
6. **Known limit.** An edit made to a legacy Computational-Log entry before the baseline export cannot be detected:
   the vault has no history. The export is therefore taken as early as Stephen authorizes it.

`CONVENTIONS.md` is repository-canonical and reached from the vault by a symlink. It is registered at its repository
path only; the vault alias is a prohibited read path for observations.

## 8. Observation and transition

### 8.1 Light path: closed reference

For an item that only ever becomes `closed_reference`:

1. A non-author observer takes a handle-bound `legacy-observation`.
2. An independent reviewer checks the observation, its families and qualifiers against the signed W0 record.
3. Stephen accepts a batch by `legacy-closed-reference-acceptance`.

There is no mapping DAG on this path, and no successor object is created. A closed-reference item is not usable by
a successor until adopted (§9). For a file that will be closed or cut over as a whole (for example
`.apm/tracker.md`), a `legacy-light-inventory` lists every item first, and the file's closure is a bijection between
that inventory's rows and accepted observations (§13.3).

### 8.2 Full path: successor owned

For a paper root becoming `successor_owned`, W9 uses W11's DAG pattern with W9 identities: observation → accepted
source inventory of the root → accepted mapping to a W9 `legacy-paper-root` record → `legacy-ownership-transitioned`.
Allowed transitions: `legacy_owned → successor_owned`, `legacy_owned → closed_reference`,
`successor_owned → closed_reference`.

**A W11 `paper` object is a separate, later step.** If Stephen wants the paper in the W11 portfolio, W11 OR-028
`AdmitResearchDossier` creates it, referencing the `legacy-paper-root` record. Its prerequisites are W11's, not
W9's: an accepted `DossierExpectedSetContent` authority chain (OR-110 to OR-115, W11 §5.1) and the programme,
hypothesis, method, dataset, claim, scope-definition and manuscript-root objects that `paper.schema.json` requires.
Dossier admission has never run live (P-058 removed it from Gate 6's route). W9 does not depend on it, and W9 never
writes a W11 portfolio object.

### 8.3 Windows

From observation to acceptance (light path) or transition (full path), the registered file's blob, or the selected
item's hash, must not change. A change aborts with no event and re-triggers observation (§4.2 item 3). Legacy
Computational-Log entries and `CONVENTIONS.md` locks are observed from their frozen baselines (§7.3), so they have
no live-file window.

### 8.4 Item granularity and targets

| Legacy item | Path | Target |
|---|---|---|
| Result file | Light | `closed_reference`; no successor object |
| Pre-registration, contract, supersession entry | Light | `closed_reference` |
| Legacy decision entry | Light, under §7.3 | `closed_reference` |
| Tracker row, Working Note, task log | Light, by a §5.5 selector, under the file's light inventory | `closed_reference` |
| Bus file | Not imported (§13.3 item 2) | — |
| Parked computation's tracker row | Light | `closed_reference`; the work re-enters as a new successor Task (§10) |
| Paper root | Full | `successor_owned` W9 `legacy-paper-root` record |
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

1. **Subject:** one accepted `closed_reference` observation, by family. For a binary or restricted input with no
   JSON family (an embedding, a null cache), the subject is the whole file: its class is the signed class of its
   producing task, or one the W0 signatory assigns, and the successor Task re-hashes it at use, where a mismatch
   suspends the adoption (item 5).
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
2. **Pre-registration:** each Task files a **new** pre-registration before dispatch. It is a typed ARS record (P-032
   makes pre-registration locks canonical ARS records); its vault Computational-Log entry is the log of it, not the
   authority. Stephen resolves it (P-005). The legacy record is not edited.
   - **Markov-2 recompute:** it cites the 2026-07-17 legacy pre-registration by identity and carries, as its own
     content, the change review finding A1 requires.
   - **T1.41:** there is no legacy pre-registration (handoff 07 §3: "pre-reg to be filed at dispatch"). The new
     pre-registration cites the 2026-07-16 double-null `[DECISION]` as its design decision, and its design answers A3
     and may answer A1 and A2.
3. **Inputs:** regenerated inside the successor Task from committed scripts at a pinned commit (for T1.41,
   `scratch/w2_fallback_audit/w2_gap_closure_table1_h1.py`, 06u §6.1). This is the preferred route. Where a legacy
   input is used instead, it is a `restricted_untracked_file` observation (§5.4): hash, size and path only, no frozen
   copy in the ARS store, and adopted first (§9). Restricted or UKDA-derived bytes never enter the ARS store.
4. **Outputs:** under the registered successor root `results/ars/` only (§3.1).
5. **W0 currency:** dispatch fires G7-A §17's trigger. A dated W0 addendum recording the pending dispatch is
   accepted by Stephen **before** dispatch, and the dispatch record cites it.
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
  before any compute. Without it, the item records `r3_family_coverage_insufficient` and does not dispatch.
- **Eligibility under P-042.** The operator chooses the session (P-042), but a named session is an eligible
  verifier route only when the dispatch record shows:
  - (a) its model family and version differ from the producer's, as recorded by the operator;
  - (b) the W4 role profile it runs under declares the capability the item's lane requires. P-042 removed
    *evaluated* provider profiles from the first release, so the evidence for (b) is the accepted W4 role profile's
    declared capability, not an evaluation result. That limit is recorded on the item;
  - (c) its context is independent of the producer's at the item's required grade (P-022, P-029).

  The record is checked before dispatch by someone other than both the producer and the second-family session
  itself: the item's independent reviewer, or Stephen.
- **If it does not:** each item records one-family review as an accepted known limit in its own decision, never as
  a precedent. Gate 6's one-family reviews were a P-058 known limit, not a precedent.

## 12. Manuscripts and pilot-promotion evidence

### 12.1 Papers transition last, as whole roots (W9-D6)

A paper root transitions only after the integration-pilot batch has passed (§14.3), and only when:

- every A-001 item feeding one of its claims is discharged (§9) or scoped out by Stephen;
- **every result family its drafts cite is either adopted for "evidence for the manuscript claims of paper X" (§9)
  or marked unadopted in a `legacy-paper-citation-status` relation**; W5 blocks any claim that rests on an unadopted
  family. The cited-family set is derived by an independent reviewer from the drafts and the claim-trace audit's
  artifact map, never by the transition's producer; it is hashed and filed before the transition, and the
  citation-status relation binds that hash;
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
| S-016 R3 provider outage | **Re-specified under P-042**: an operator-mediated second-family session is unavailable → `r3_family_coverage_insufficient`; its `unable_to_grade` H row stays. Because S-016 is in the W6 catalogue accepted under P-027, the change needs a dated W6 addendum (as 06a and 06b were), not only W9-D12b |

Per-item applicability is proposed by the item's independent reviewer and fixed by Stephen in the batch decision,
never by the item's producer. An exclusion (F-024, S-016's H row) is an owner-accepted record.

## 13. Rollback, recovery and deprecation

### 13.1 Rollback (W9-D4)

- **Before commit:** any stop leaves the item `legacy_owned`; no event; no change to the legacy file.
- **After commit, closed-reference item:** the accepted record is superseded by `legacy-record-supersession`
  (§13.2); the old record and its events stay.
- **After commit, paper root:** recovery creates a **new `legacy-paper-root` successor record** that cites the
  transitioned one by lineage. The recovery root binds the predecessor root and Stephen's recovery Decision, not a
  transition event. Or Stephen declares a **manual-operation mode** (04-plan §7: "return the greenfield paper to
  manual operation"). In manual-operation mode the root stays `successor_owned` and ARS events stay canonical (W2
  §22.3): one named human writer edits the files, and each edit enters as an attributed ARS event that registers the
  new file bytes under that human actor. If the control store itself is what failed, or 04-plan §7's "retire the
  prototype" applies, the human writer's edits are attributed Git commits on a named branch, and they are imported
  as events once a store is available again. There is no unattributed write and no second mode. Authority never
  returns to `legacy_owned` or to APM.
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
3. **Tracker and logs:** a `legacy-light-inventory` is taken for `.apm/tracker.md` (every task row and Working Note,
   with blocker rows) and for the task-log set; each item is then observed by its §5.5 selector and accepted
   `closed_reference` by the light path.
4. **Writer revocation for `.apm/`:** sessions stop writing Working Notes to `.apm/tracker.md` (the #368 case);
   Stephen records the revocation; the §4.4 detector watches the path.
5. **Final observation and closure** of the whole `.apm/` set:
   - a **file-level inventory** first lists every file: the 34 tracked files (`git ls-files .apm` at the observation
     commit), the untracked `.apm/memory/stage-NN/` logs and the bus directory. Each file maps to exactly one file
     closure (a light inventory plus accepted observations) or one non-import record (such as the bus inventory);
   - each file's final light inventory, re-observed after revocation, must be in bijection with its accepted
     observations, with no blocker row left.

   A missing or extra file or item blocks closure.
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

The integration pilot measures the import machinery (recall of governing records, operator burden, defects). It
does not measure research-workflow context, so 04-plan §6's research criteria stay unmeasured until successor compute
(§10) runs; the Phase F decision should say so.

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

**Thresholds** are filed by Stephen as a hashed, dated pre-registration before the batch's first acceptance. The
vault has no history and file times are mutable, so the hash is anchored in a Git commit or an ARS event that
precedes the first acceptance; that anchor, not the vault date, is what W9-T16 checks. A missed threshold stops further batches. It cannot reverse committed records; those are superseded only
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
| W9-D5 | Detectors (§4.4) | Keep the existing ruleset 20822054 and record its bypass list (`RepositoryRole` 5, `pull_request` mode) as a configuration read before each batch; add the post-merge detector with the `results/` prefix rule and rule-suite reads for bypass use, and the baseline-backed vault and `CONVENTIONS.md` checks; each detector watched to fail before the first registration |
| W9-D6 | Paper granularity (§12.1) | Whole root, last, as a W9 `legacy-paper-root` record (decided, N-1) with no transition ref; citation status in a separate relation over an independently derived, frozen cited-family set |
| W9-D7 | Manuscript review (§12.2) | Wait for Gate 9 for prose |
| W9-D8a | Evidence register | A dated W9 addendum to `01-current-system-evidence.md` before acceptance |
| W9-D8b | Projection namespace (§7.2) | `.research-system/projections/legacy/`, registered under the W9 family |
| W9-D8c | Discovery observation (§15) | Yes: a non-author, read-only, dated observation before W9's acceptance |
| W9-D9 | Shared-writer exception (§7.3) | Accept, with the object-then-date legacy set (Stephen accepts the classified list); a Git-anchored export for the log and the `4b143c92` blob for `CONVENTIONS.md`; transitions only from the baselines; the insertion-only rule and the detectors |
| W9-D10 | W9 catalogue and its genesis (§5.3) | Accept: a store named by the implementation plan and decided by Stephen, never the Gate 6 store; a separately accepted W9 bootstrap contract; a scoped owner grant; W11 genesis first in a new store; P-059 protected-identity re-acceptance for the new commands |
| W9-D11 | Adoption semantics (§9) | Accept `AdoptLegacyAuthority` as Stephen-only, use-scoped and revalidating |
| W9-D12a | Integration-pilot rubric and Phase F wider-adoption authorization (§14.2) | Accept the rubric; authorize wider adoption separately, after the pilot |
| W9-D12b | S-016 under P-042 and F-024's exclusion (§12.3) | Accept both; S-016's change lands as a dated W6 addendum; F-024's exclusion is for P01 only and is reassessed at P04's intake |
| W9-D13 | P04 and other legacy result families (§3.2) | `legacy_owned`, unregistered until their own intake, guarded meanwhile by the `results/` prefix rule (§4.4) |
| W9-D14 | Shared enforcement surfaces and the successor results root (§3.1, §4.3) | Accept the `shared_enforcement_surface` split, with the reviewer deriving affected results; register `results/ars/` as the `successor_results_root` so the detector exempts exactly that prefix |

### 16.2 Amendments carried to G7-C (old→new texts)

| Source | Old | New (proposed) |
|---|---|---|
| P-026 legacy boundary | "the foundation cannot write, migrate, normalize, or promote their tasks, evidence, decisions, or claims" | "…except through W9's attributed observation, adoption and per-item transition, each resolved by Stephen; nothing is written to legacy files" |
| 04-plan §2 | "never migrated into the prototype and are never used as live pilot inputs" | "enter ARS only by W9 observation, adoption and per-item transition; legacy files are never written" |
| 04-plan §5 exclusion | "imports that promote legacy evidence into successor authority" | "imports that promote legacy evidence without a W9 adoption decision" |
| P-034 boundary (consequential) | "The P-026 legacy boundary is unchanged: T1.28 and the two current APM-managed papers remain `legacy_owned`; T1.28 terminal review still gates legacy deprecation claims." | "The P-026 legacy boundary, as amended through G7-C, holds: the two papers remain `legacy_owned` until their W9 transition; T1.28's terminal review is recorded (G7-A, accepted 2026-10-22) and now binds legacy deprecation claims only through A-001 (G7-A §10)" |
| 04-plan §6 (pilot initialization) | "The pilot paper is initialized under ARS from inception." | "The system pilot (Gate 6's SPEC-01 run) was initialized under ARS from inception; legacy papers enter only by W9 transition" |
| 04-plan §6 (pilot scope) | "Initial pilot work should use bounded R0/R1 tasks and one representative R2 workflow before any paper-critical computation." | Unchanged for new ARS work; for legacy integration, "the Gate 7 integration pilot follows W9 §14.2's rubric before any paper-critical computation" |
| Roadmap §4 | "be the first paper initiated after the two current APM-managed papers, not an active or historical migrated task;" | "the system pilot was Gate 6's SPEC-01 run; the Gate 7 integration pilot follows W9 §14.2; wider adoption needs Stephen's separate authorization" |
| 06l Step 5 | "Rollback returns the item to its prior authority" | "Before commit, a stop leaves the item `legacy_owned`; after commit, recovery is successor-side (W9 §13.1)" |
| 06l Step 5 proof | "and a tested rollback handle for that item" | "and, for that item, the pre-commit abort path and its named post-commit supersession or recovery route, each exercised once on a scratch store (W9 §13.1)" |
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
| W9-T6 | A change in a window aborts | Change the blob, or the selected item's hash, after observation; no event |
| W9-T7 | Detectors fire | Replay `5df0c001` and `811d5a2b`; edit a legacy log entry; each flagged |
| W9-T8 | No successor use without adoption | Reference an unadopted closed-reference family in a successor Task; rejected |
| W9-T9 | Adoption revalidates | Re-observe an adopted source with a new blob; the adoption suspends |
| W9-T10 | Parked compute writes nothing legacy | A successor Task writing a legacy path or legacy pre-registration; rejected |
| W9-T11 | Restricted bytes stay out of the store, on every path | Register a `*.pkl` or null cache as an ARS artefact, or observe one with a frozen copy in the store; both rejected |
| W9-T12 | Family coverage at dispatch | Dispatch an R3 item with no second-family session named; blocked before compute |
| W9-T13 | Corrections bind generally | Import any decision entry with a `corrected_by` relation; values come from the canonical source |
| W9-T14 | Supersession is acyclic and keeps history | Supersede a record twice in a cycle; rejected; old events intact |
| W9-T15 | Paper recovery changes no accepted artefact | Recover a transitioned paper; every legacy blob unchanged |
| W9-T16 | Thresholds precede the batch | A threshold whose anchoring commit or event follows the batch's first acceptance; the batch is invalid |
| W9-T17 | A paper transition cannot bypass adoption | Transition a root whose citation-status relation omits a family in the frozen cited-family set, or whose drafts cite a family missing from that set; rejected. A family marked unadopted blocks its claims in W5 |
| W9-T18 | Closure is a bijection | Close `.apm/tracker.md` with one row missing from the accepted observations, or with a blocker row; closure blocked |
| W9-T19 | Legacy entries and locks match their baselines | Edit a byte of a legacy log entry, rename a legacy heading, or modify a legacy `CONVENTIONS.md` bullet; each flagged. Insert a successor bullet into a legacy section; not flagged |
| W9-T20 | The Gate 6 store is never a W9 target | Point the W9 genesis at `TDL-ARS-G6-Control`; refused |
| W9-T21 | The paper-root records are acyclic | A `legacy-paper-root` that names its transition event, or a cycle among root, mapping and transition; rejected |
| W9-T22 | Duplicate anchors block | A tracker with two rows for one task ID; that region is a blocker row, and closure is blocked |

## 18. Independent review and exit gate

- [x] Independent adversarial review of draft 0.1 (REWORK REQUIRED; `b7fd4415`).
- [x] Author reconciliation of draft 0.1's findings (draft 0.2).
- [x] Focused re-review of draft 0.2 (REWORK REQUIRED, narrow; `6ac30e2e`).
- [x] Author reconciliation of the re-review (draft 0.3); narrow re-check REWORK REQUIRED, narrow (`b51d3728`).
- [ ] Author reconciliation of the re-check (draft 0.4) and its re-check.
- [ ] Stephen's decisions W9-D1 to W9-D14.
- [ ] The §15 Discovery observation, if W9-D8c is accepted.
- [ ] The evidence-register addendum (W9-D8a).
- [ ] Stephen's acceptance of the exact reconciled revision, conditional on G7-C's register entry (§16.2).

Acceptance of W9 opens nothing, transitions nothing and authorizes no implementation.
