# G7-B focused re-review: W9 draft 0.2 at `34ac441e`

**Date:** 2026-10-22
**Reviewer:** the same independent session that reviewed draft 0.1 (`b7fd4415`); not the W9 author
**Skill:** `adversarial-design-review` (remediation re-review mode), with `research-observer` running
**Runtime authority:** none. This report edits no other file and commits nothing. Nothing was written to
`papers/`, `.apm/`, the vault, any ARS store, GitHub or Jira.

## 1. Subject and verification base

| Identity | Value |
|---|---|
| File | `docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md` |
| Commit | `34ac441e91c36356733bfd298b68d016b31bd49d` on `claude/gate7-prep-docs-5202cf` |
| Blob | `55b84e92c1acdcd525b12c4450c878fd896e828d` (confirmed with `git rev-parse 34ac441e:<path>`) |
| Bytes | `git show 34ac441e:<path>`, 687 lines. `W9:N` below means those lines. |
| Reconciliation read | `reviews/g7b-w9-reconciliation-2026-10-22.md` at `34ac441e` (83 lines) |
| origin/main verified against | `3fa437a160ab75c5fa0083fd35176006b1ee19a4` (after `git fetch origin`; unchanged) |

Commit `d2e09eea` (`docs/w11-limb1-acceptance-record`, landing the stranded W11 limb-1 record) was inspected by
`git show --stat` only. It is not on main (`git merge-base --is-ancestor d2e09eea origin/main` fails), so main's
register is treated as unchanged.

## 2. Verdict

**REWORK REQUIRED (narrow).**

| Severity | Count |
|---|---|
| Blocking | 0 |
| Major | 6 |
| Minor | 11 |
| Info | 4 |

Draft 0.2 is a real repair. Route (ii) takes W9 off W11's accepted schemas. Adoption now exists, is
Stephen-only and revalidates. W0 classes come only from signed records. The writer list matches G7-A §11. The
fixture set is derived from the 05-plan deferred list. The Discovery condition is honestly left open. Ten of the
fourteen prior findings are closed.

Six new Majors remain, and all are narrow:
- The full path still lands on a W11 object that no accepted W11 command can create outside dossier admission
  (N-1).
- The W9 genesis has no named store (N-2).
- The light path cannot address the row-level items it promises, so the `.apm/` closure has no completeness check
  (N-3).
- A paper-root transition is a second route to successor use that skips adoption (N-4).
- Observations of untracked files demand a frozen copy that the restricted-data rule forbids (N-5).
- The §7.3 exception does not say which log entries are "legacy" and has no baseline for its detector (N-6).

None needs a new route decision. Each is fixable with text.

## 3. Closure table for draft 0.1's Blocking and Major findings

| 0.1 finding | Status | Evidence in 0.2 |
|---|---|---|
| **B-1** W11 reuse infeasible | **Partly closed** | Closed for the light path and the W9 records: §5.1 (`W9:216-228`) lists exactly the schema facts the review cited; the `ars://legacy/` family (`W9:236-243`) has its own registration root, source-identity kinds, JSON-pointer membership and catalogue, and W9 no longer touches any W11 schema. Two gaps remain. The full path maps to "a W11 `paper` object" (`W9:242`, `W9:362`, `W9:381`) that no accepted W11 command can produce outside dossier admission (N-1). The one-time W9 genesis (`W9:247-250`) names no store and omits W11 §1 item 7's bootstrap-contract condition (N-2). |
| **M-1** adoption undefined | **Partly closed** | §9 (`W9:399-416`) defines `AdoptLegacyAuthority`: one observation, by family; Stephen only; use-scoped W5 admissibility; qualifiers stay attached; suspended on re-observation, new qualifier or supersession. `legacy-discharge-relation` closes A-001 items under W0-D1. A1–A4 are carried as `open_review_finding` (`W9:308`). Gap: a paper-root transition makes legacy drafts successor-owned with no adoption of the families they cite (N-4). |
| **M-2** unsigned W0 classes | **Closed** | `W9:41-42`, `W9:204`, `W9:238` ("per-family W0 class with the **signed** W0 revision and signature record") and `W9:387`. All eight §14 items must be signed before any closed-reference acceptance. |
| **M-3** wholesale globs; writer list | **Closed** | Exact-file registration (`W9:123`). `W9:163-164` add #168, #169 and #334, matching G7-A §11 (`G7-A:341-352`). Successor root `results/ars/` (`W9:137-138`). `shared_enforcement_surface` split (`W9:180-185`). Residual registry-closure point: n-11. |
| **M-4** class (b) loophole; client-side guard | **Closed** | Class (b) needs Stephen's note with old and new blobs plus an independent semantic-equivalence review; the writer's own note does not qualify (`W9:171-173`). Any blob change re-triggers observation (`W9:177-178`). Three detectors, with the `5df0c001`/`811d5a2b` replays as negative controls (`W9:189-197`). Both commits are on main's first-parent chain (`git log --first-parent`), so a first-parent detector sees them. Residuals: n-2 (a server-side ruleset already exists), n-3. |
| **M-5** shared-writer files | **Partly closed** | §7.3 (`W9:328-344`): heading-anchored entry hash, prepend-only, entry-hash window, vault detector, frozen-export alternative; `CONVENTIONS.md` at its repository path only. Gap: the set of "legacy" entries and locks is undefined, and the vault detector has no baseline (N-6). |
| **M-6** uncommitted sources; bus | **Partly closed** | `untracked_file`/`vault_file` identity kinds with "no Git identity" as a non-inference (`W9:236-238`). The bus is not imported, with a dated closure inventory (`W9:529-531`). A seven-step deprecation path (`W9:526-537`). Gap: no selector or inventory for tracker rows and task-log items, so step 5's "closure" has no check (N-3). |
| **M-7** parked-compute contradictions; restricted inputs | **Partly closed** | New pre-registration citing the legacy one, resolved by Stephen, legacy record not edited (`W9:423-427`). Restricted bytes never in the ARS store (`W9:428-432`). Outputs under `results/ars/`. The G7-A §17 trigger is recorded (`W9:434-435`). Gaps: N-5, and the labelling and ordering points in n-5. |
| **M-8** post-commit rollback | **Closed** (residual n-6) | Closed-reference items: `legacy-record-supersession` keeps the old record and re-points current use (`W9:243`, `W9:520-524`). Paper roots: a new successor paper object, or a manual-operation mode (`W9:511-514`). The "tested rollback handle" is redefined and exercised on scratch (`W9:516-517`). 06l Steps 5–7 old→new texts are in §16.2. |
| **M-9** pilot rubric missing | **Closed** | §14.2 (`W9:572-585`): closed-reference items only, at most 20, supersedable, no paper root, no claim-bearing adoption, no compute; papers last; Phase F authorization is a separate decision. Residual: n-9. |
| **M-10** unmeasurable metrics | **Closed** (residual n-8) | Recall denominator compiled and hashed by an independent reviewer before the batch; one W3 reference tokenizer (P-028); cost added; thresholds as a hashed, dated pre-registration; a miss stops further batches (`W9:589-600`). |
| **M-11** fixture set not closed | **Closed** (residual n-7) | §12.3 (`W9:476-502`) covers the whole 05-plan §4.4 deferred list: F-006, F-015–F-019, F-023, F-024, F-029, F-030, F-037, F-038, S-005, S-007, S-014–S-016. Each is assigned or excluded. Names match W6 (`06:170,179-183,187-188`). Applicability is set by the reviewer and Stephen, never the producer. |
| **M-12** W9-D3 scope and timing | **Closed** (residual n-7) | §11.2 (`W9:448-458`) re-frames the question as survival under P-042. The check is at dispatch over P-005's full R3 set, including adoption. Otherwise a per-item known limit. |
| **M-13** Discovery inventory with no rows | **Closed** | `W9:606-610`: "This section is not that inventory"; W0-D4's condition stays open until a non-author observation is accepted. P04's mode is W9-D13. |

Minors and infos from 0.1 that 0.2 changed were re-checked: m-1 (residual n-1), m-2, m-3, m-4, m-5, m-6 (residual
n-10), m-7, m-8, m-9 (residual n-9), m-10, m-11 and m-12 are closed. I-5 is acted on outside W9 (d2e09eea,
unmerged). I-6 is adopted (`W9:151-152`).

## 4. New findings

### Major

#### N-1. The full path's target, "a W11 `paper` object", has no producer W9 names; only W11 dossier admission can publish one

- **Claim.** The full path maps a paper root "to a W11 `paper` object" (`W9:242`, `W9:361-362`, `W9:381`). W11 is
  "Unchanged" (`W9:102`).
- **Evidence.**
  - None of W11's 81 owner rows registers a `paper`. OR-001 to OR-041 (`11:490-530`) create Candidates (OR-001,
    OR-029) and Discovery records. W11 publishes portfolio objects only through `AdmitResearchDossier` (OR-028; W11
    §1 item 4), which needs the accepted six-family `DossierExpectedSetContent` authority chain (OR-109 to OR-115,
    §5.1).
  - P-058 removed `bootstrap_dossier_authority` and `admit_dossier` from Gate 6's required route, so dossier
    admission has never run live.
  - The accepted `paper.schema.json` requires `programme_ref`, `hypothesis_refs`, `method_refs`, `dataset_refs`,
    `claim_refs`, `scope_definition_refs` and `manuscript_root_ref`. Creating a P01-A `paper` therefore first needs
    a programme object and the other referenced objects.
- **Failure.** The paper-root transition cannot run without either an unplanned dossier admission (expected-set
  authority, six-family closure) or a new W9 command that writes a W11 portfolio kind. The second is outside W11's
  closed owner universe (W11 §8.1, `11:1558`), which reopens B-1.
- **Impact.** The full path is not executable as written.
- **Disposition.** Fix now.
- **Required correction.** State that the paper target is created by W11 OR-028 dossier admission and list its
  prerequisites (expected-set authority, programme and other referenced objects), with an owner decision on that
  route. Or make the full-path target a W9-owned `legacy-paper-root` record that a later W11 dossier admission
  references. Either way, add the step to §4.5's paper-root row.
- **Affects.** §§5.2, 8.2, 8.4, 4.5; W9-D6, W9-D10; W11 §5.

#### N-2. The W9 genesis route does not name its store or carry W11 §1 item 7's conditions

- **Claim.** The W9 catalogue is "imported into the store by its own one-time W9 genesis transaction"
  (`W9:247-250`).
- **Evidence.**
  - P-058 step 6 (`03:3657-3658`): "The durable checkout stays frozen at M2, and the store at 91 events." The Gate
    6 store `TDL-ARS-G6-Control` is historical evidence.
  - W11 §1 item 7 requires "a separately accepted minimal bootstrap contract" and says the runtime "cannot produce or
    accept its own prerequisite".
  - The Gate 6 genesis needed an owner grant scoped to the catalogue stream (P-058 Step 3 batch 1, `03:2705-2722`).
  - A new store would also need W11's genesis again, because the full path references W11 objects. W9 does not say
    whether W11's one-time genesis is one-time per store.
  - New W2 commands touch the protected append-path census and tree identities that P-059 re-accepted at exact
    bytes.
- **Failure.** "The store" is read as the Gate 6 store and W9 genesis appends to frozen Gate 6 evidence. Or a new
  store is created whose W11 genesis has no accepted authority. Either way, the bootstrap trust boundary that W11
  §1 item 7 protects is crossed without a record.
- **Impact.** Authority; provenance of the catalogue.
- **Disposition.** Fix now, as part of W9-D10.
- **Required correction.** Name the target store, or require one to be named in the implementation plan with
  Stephen's decision, and state that the Gate 6 store is not appended to. Require a separately accepted W9
  bootstrap contract and an owner grant scoped to the W9 catalogue stream. If the store is new, state the W11
  genesis it also needs. Name the W2 census and protected-identity re-acceptance the new commands require.
- **Affects.** §5.3; W9-D10; P-058; P-059.

#### N-3. The light path is per file, but §8.4's items are rows; tracker rows and task logs have no selector and the `.apm/` closure has no completeness check

- **Claim.** `legacy-observation` is "one handle-bound observation of one registered file" (`W9:238`). §8.4 makes
  "Tracker row, task log" light-path items (`W9:378`). §13.3 step 5 calls for "Final observation and closure of
  the whole `.apm/` set" (`W9:535`). The light path has "no inventory or mapping DAG" (`W9:356`).
- **Evidence.** The only sub-file selectors W9 defines are JSON-pointer families (§6.2, for JSON) and the
  heading-anchored entry hash, which §7.3 restricts to the Computational-Log and `CONVENTIONS.md`. `.apm/tracker.md`
  is Markdown. W11 uses its source-only inventory precisely to prove that no row was omitted (W11 §7.6.1:
  "Unknown/unparseable regions are blocker rows, never omissions").
- **Failure.** A tracker row is either observed as the whole file (so one row's acceptance binds every row and
  later Working Notes) or not addressable. A row that is never observed stays silently `legacy_owned`, and the
  `.apm/` closure in step 5 has nothing to compare against. That is silent absence on the deprecation path.
- **Impact.** Required deprecation content is partly unexecutable.
- **Disposition.** Fix now.
- **Required correction.** Define a row selector for `tracker.md` (for example a task-ID-anchored row hash) and a
  frontmatter selector for task logs. For any file that will be closed or cut over, require a light inventory: a
  complete row list with blocker rows for unparseable regions, independently reproduced. Make step 5's closure a
  bijection between that inventory and the accepted observations.
- **Affects.** §§5.2, 8.1, 8.4, 13.3.

#### N-4. A paper-root transition is a second route for legacy content into successor use, outside adoption

- **Claim.** "Nothing legacy reaches successor use until an `AdoptLegacyAuthority` decision (§9) binds it"
  (`W9:27-28`). A paper root becomes `successor_owned` by the full path (`W9:359-364`, `W9:381`), with §12.1's
  preconditions (`W9:464-469`).
- **Evidence.** §12.1 requires A-001 items discharged, the Stage 2 scope, audit verdicts as qualifiers and the A1
  fork for rung-4/5 claims. It does not require the result families that the root's merged drafts cite to be
  adopted. A `merged_draft` "stays `legacy_owned` until its paper root transitions" (`W9:261`) and is then
  successor-owned by the transition alone.
- **Failure.** After the transition, P01-A's drafts, including their numeric claims, are successor-owned
  manuscript text. They cite closed-reference families that were never adopted, so the cited evidence never had
  Stephen's per-family P-005 upgrade for that use. §1 item 1's rule holds for Tasks but not for prose.
- **Impact.** An evidence-to-claim gate is bypassed; this is the failure class M-1 was about.
- **Disposition.** Fix now.
- **Required correction.** Add to §12.1: before a root transitions, every result family its drafts cite is
  adopted for "evidence for the manuscript claims of paper X", or each citation is marked unadopted, and W5 blocks
  any claim resting on it. Add a test: transition a root citing an unadopted family; its claims are blocked.
- **Affects.** §§1, 8.2, 9, 12.1, 17; W9-D6, W9-D11.

#### N-5. Observing an untracked restricted file requires a frozen copy that §10 forbids in the store

- **Claim.** For untracked and vault files, the source identity is a "handle-bound SHA-256 plus a dated frozen
  copy" (`W9:238`). Restricted or UKDA-derived bytes "never enter the ARS artefact store" (`W9:429-431`). "Legacy
  embeddings that a successor Task uses are adopted first" (`W9:431-432`), and adoption's subject is an accepted
  observation (`W9:404`).
- **Evidence.** Embeddings and null caches are gitignored and UKDA-derived (W0 §10.3; CLAUDE.md output rules).
  Adopting one therefore requires observing it, which requires a frozen copy. W9 does not say where that copy
  lives. W9-T11 rejects registering a `*.pkl` as an artefact (`W9:670`), which conflicts with the observation
  rule.
- **Failure.** An implementer either stores frozen copies of restricted-derived bytes in the ARS store (a
  data-governance breach) or cannot adopt the embeddings §10 needs.
- **Impact.** Data governance; the compute route is blocked.
- **Disposition.** Fix now.
- **Required correction.** Add a `restricted_untracked_file` identity kind: hash, size and path only, no frozen
  copy, with the absence recorded as a non-inference, and any frozen copy kept under `PROJ_ROOT` outside the
  store. Prefer regeneration (§10 item 3) over adopting restricted files. Make W9-T11 cover the observation path.
- **Affects.** §§5.2, 9, 10; W9-T11; W9-D1.

#### N-6. The §7.3 exception does not define which entries and locks are "legacy", and the vault detector has no baseline

- **Claim.** "No byte inside a legacy entry or lock changes" (`W9:336-337`). The vault detector flags "an edit to
  any legacy entry's bytes" (`W9:193`).
- **Evidence.**
  - The vault is not under Git (shown in the 0.1 review), so there is no history to diff against.
  - Successor sessions write P01 entries: the 2026-10-22 "P01-A: CORRECTION to the 2026-07-11 T1.20 [DECISION]",
    and the five P06 G7 entries above it (`Computational-Log.md:1-67`).
  - W9 gives no rule (date of the freeze, author, paper label) that classifies an entry as legacy or successor.
    The same holds for `CONVENTIONS.md` locks.
  - The detector can only compare against hashes it already holds, and observations are taken per item later.
- **Failure.** An edit to a legacy entry made before its first observation becomes the accepted "legacy" bytes
  with no signal. A successor-written correction is either protected as legacy (and can then never be corrected
  itself) or left unprotected.
- **Impact.** The shared-writer exception's single invariant is unenforceable at its start.
- **Disposition.** Fix now, as part of W9-D9.
- **Required correction.** Define the legacy set: for example every entry dated before the 2026-07-18 freeze
  merge, plus named later owner-ruled legacy entries; successor entries are everything else. At registration,
  take a dated, hashed baseline export of every legacy entry and lock, observed by a non-author. The detector
  compares the live file against that baseline. Alternatively, make §7.3 item 5 (transition only from a frozen
  export) the default.
- **Affects.** §7.3, §4.4; W9-D9; W9-T7.

### Minor

- **n-1. W9-A1's range is incomplete (`W9:78`).** W11's legacy commands are OR-031 `RecordLegacyPortfolioObservation`,
  OR-032 and OR-033 (`11:520-522`); OR-122 to OR-139 are their authority rows. Grep over `research_system/` and
  `tests/` finds no handler for any of them. Say "OR-031 to OR-033 and OR-122 to OR-139".
- **n-2. Server-side protection already exists (`W9:191`).** `gh api repos/stephendor/TDL/rulesets/20822054`: ruleset
  "P-049 Gate 6 main merge admission", `enforcement: active`, on `refs/heads/main`, with `pull_request`,
  `required_status_checks`, `merge_queue` and `non_fast_forward` rules. It was created 2026-08-13, after both
  direct pushes (2026-08-05 and 2026-08-07). Its bypass list holds RepositoryRole 5 in `pull_request` mode. Classic
  branch protection returns 404. Cite the ruleset, make the negative control check its bypass list, and say that
  it postdates `5df0c001` and `811d5a2b`.
- **n-3. The `shared_enforcement_surface` writer names the affected legacy results itself (`W9:182-184`).** That
  reintroduces self-attestation. Have the independent reviewer derive the affected set from the contract's binding
  tests.
- **n-4. Record-level inconsistencies in §5.2 and §8.4.** `legacy-repository-path-registration` takes a
  "repository root ID" but also registers `vault_file` sources, so it needs a vault root too. The role list has no
  projection role, yet W9-D8b registers the §7.2 projection "under the W9 family". §8.4's bus row cites "§7.4 of
  the deprecation path", which does not exist; it means §13.3 item 2.
- **n-5. §10 item 2 mislabels and misorders.** T1.41 has no legacy pre-registration: handoff 07 §3 says "pre-reg to
  be filed at dispatch". The "2026-07-16 double-null `[DECISION]`" (`Computational-Log.md:2036`) is a decision. The
  new pre-registration is filed "in the vault", but P-032 makes pre-registration locks typed ARS records; the vault
  entry should be its log, not the authority. Item 5 calls the G7-A §17 addendum a "precondition" that the
  dispatch itself triggers; say whether it must be accepted before dispatch or follow it.
- **n-6. Manual-operation mode has no ownership definition (`W9:512-514`).** A `successor_owned` root written by
  one human outside ARS commands conflicts with W2 §22.3 ("ARS events are canonical"). Say whether the root moves
  to a declared mode, or how manual writes enter as attributed events.
- **n-7. S-016 and the family check.** Re-specifying S-016 changes a fixture in the W6 catalogue accepted under
  P-027. W6 owns that catalogue, and its earlier changes were made by dated W6 addenda (06a, 06b), so this one
  needs a W6 addendum too, not only W9-D12b. In §11.2,
  "the operator names the second-family session" is not P-029's "eligible verifier route at the required
  capability and independence grade". Say what makes a named session eligible under P-042.
- **n-8. Threshold dating is not anchored (`W9:598-599`).** "A hashed, dated pre-registration in the vault" cannot
  prove its date: the vault has no history and file times are mutable. Anchor the hash in a Git commit or an ARS
  event before the first acceptance, so W9-T16 is checkable.
- **n-9. §16.2 text and coverage (`W9:646-654`).**
  - The 04-plan §6 row's old text, "the first paper initiated after the two current APM-managed papers", is from
    roadmap §4. 04-plan §6 says "The pilot paper is initialized under ARS from inception" and "bounded R0/R1 tasks
    and one representative R2 workflow before any paper-critical computation"; quote and amend each separately.
  - P-034's "The P-026 legacy boundary is unchanged" needs a consequential old→new.
  - 06l Step 5's "a tested rollback handle for that item" (proof before Step 6) is redefined in §13.1 but carries
    no old→new.
  - The other old texts match their sources verbatim: P-026, 04-plan §2, 04-plan §5, and 06l Steps 5, 6 and 7.
- **n-10. §4.5 has no row for successor compute dispatch (`W9:201-210`),** probably the first Gate 7 action (T1.41).
  Name its gates: Gate 7 opening, W9-D3 coverage, the new pre-registration, F-016/F-029/F-030 evidence, the W8
  grant, any input adoption and the G7-A §17 addendum.
- **n-11. Registry closure.** Registration covers files named in the W0 manifest §5.2, G7-A §6 and audit §3.2, plus
  "the others the inventory finds" (`W9:127-128`). P04 and the other families stay unregistered (W9-D13). Any
  legacy result file outside those lists is invisible to the §4.4 detector. Add a prefix rule to the post-merge
  detector, for example any change under `results/` outside `results/ars/` without a §4.2 record is flagged,
  while registration stays per file.

### Info

- **I-a.** d2e09eea prepares the stranded W11 limb-1 record (03 +90/−12, the 2026-08-01 acceptance file, two
  READMEs). It is not on main. W9's §2.1 W11 row (`W9:73`) is correct about the stranded state as of
  `3fa437a1`.
- **I-b.** New identities checked and present at origin/main: `lm_sensitivity_L2500_frozen_2026-05-28.json`,
  `lm_sensitivity_L8000_frozen_2026-05-28.json`, `dedup_amendment_comparison_2026-06-01.json`,
  `dedup_amendment_comparison_corrected_2026-07-14.json` and `w2_fallback_audit_2026-07-14.json`. The dedup family
  split in `W9:283` matches `SUPERSEDED.md:30-37` ("H1 W₂ cell and the decision_summary counts" from the corrected
  file; "landscape-L², `dedup_provenance` and the probes" from the 06-01 file).
- **I-c.** §3.2's "the APM freeze covered P04's prose" holds: the CONVENTIONS lock says "No manuscript prose is
  authored by APM-dispatched agents" with no paper restriction (`CONVENTIONS.md:37-41`).
- **I-d.** §7.3 asks for "a bounded exception to 06l §4 and W11 §7.1" (`W9:330-331`). W11 §7.1 governs only its
  four Discovery vault paths, and W9 no longer uses W11's registry. An exception to W11 §7.1 is unnecessary and
  reads as amending accepted W11. Cite 06l §4 only.

## 5. Reviewer opinion on W9-D1 to W9-D14

This section is **reviewer opinion**. Stephen decides.

| ID | Opinion |
|---|---|
| W9-D1 | **Agree**, with n-5 (T1.41 has no legacy pre-registration; the new one is an ARS record) and N-5 (prefer regeneration over adopting restricted files). |
| W9-D2 | **Agree.** |
| W9-D3 | **Agree with the recommended branch**, adding a defined eligibility test for the second-family session (n-7). Whether P-042's "provider-runtime portions" include the family rule is an interpretation only Stephen can make; the decision should say so. |
| W9-D4 | **Agree**, after manual-operation mode gets an ownership definition (n-6). |
| W9-D5 | **Agree.** Cite the existing ruleset (n-2), add the `results/` prefix rule (n-11) and a vault baseline (N-6). |
| W9-D6 | **Agree.** Whole root, last, with N-4's adoption precondition. |
| W9-D7 | **Agree.** |
| W9-D8a | **Agree.** |
| W9-D8b | **Agree in principle**; the W9 role list needs a projection role first (n-4). |
| W9-D8c | **Agree.** |
| W9-D9 | **Agree only with N-6's legacy-set definition and baseline.** Otherwise I would make §7.3 item 5 (transition only from a frozen, dated export) the default for legacy entries: it removes live-file windows altogether. |
| W9-D10 | **Agree in principle**, conditional on N-2 (named store, a bootstrap contract, a scoped grant, W2 census re-acceptance) and N-1 (the paper target). |
| W9-D11 | **Agree**, with N-4 so that paper transitions cannot bypass it. |
| W9-D12a | **Agree with the rubric.** Note in the Phase F decision that the integration pilot measures the import machinery's recall and burden, not research-workflow context. 04-plan §6's research criteria then remain unmeasured until compute runs. |
| W9-D12b | **Agree.** S-016 belongs in a W6 addendum (n-7). F-024's exclusion is for P01 only and should be reassessed at P04 intake. |
| W9-D13 | **Agree**, with n-11's prefix detector so that unregistered families are not unguarded. |
| W9-D14 | **Agree with both the split and `results/ars/`**, with n-3. Register `results/ars/` as the successor root so that the detector exempts exactly that prefix. |

## 6. Practicality

The light path is the right economy: one observation, one review, one batch decision for items that never become
successor objects. Draft 0.2 adds nine record types. That is proportionate only if N-3's light inventory stays
light: a row list with blocker rows, not W11's full reproducer chain. The full chain should remain only for paper
roots. N-1 matters for cost too: if the paper target goes through W11 dossier admission, the paper-root
transition inherits the full six-family expected-set authority, and that should be visible now, not discovered
at Gate 7 execution.

## 7. Limits

- **Same model family.** I run on Claude Opus 5.5, the same family as the author, and I also reviewed draft 0.1, so
  this re-review is not independent of my own earlier framing. That is a P-058 known limit; a second-family pass
  would reduce it.
- **Not read, by instruction:** anything under `papers/` and the vault Discovery backlog. The Computational-Log was
  read only by Grep, for headings and the cited entries.
- **External reads:** one GitHub ruleset and branch read via `gh api`; no writes. No Jira read in this round.
- **Not verified:** whether the 05b tranche executed S-014 to S-016 to completion (only that it was planned and that
  Gate 5 was accepted); d2e09eea's content beyond its file list; the JSON key layout of the two `lm_sensitivity`
  files.
- **No tests were run.** This is a design re-review.

## 8. Change log

- 2026-10-22: report created. No other file edited.
