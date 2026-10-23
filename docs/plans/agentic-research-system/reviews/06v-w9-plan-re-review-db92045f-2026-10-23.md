# 06v re-review: the W9 implementation plan, revision 2, at `db92045f`

**Date:** 2026-10-23
**Reviewer:** the same independent session that reviewed revision 1 (`b3fe778c`). It is distinct from the 06v author,
and it did not author or review W9, G7-A or G7-C.
**Skill:** `adversarial-design-review`, with `research-observer` running
**Scope:** narrow, as Stephen asked through the author session:
1. whether M-1 to M-8 and m-1 to m-13 are closed;
2. the new or rewritten sections (§2.2 shared-replay and writer-lock rows, the §2.3 consequence, §2.6, §2.7, §2.8,
   O-32 to O-38, §7, and D-1 to D-8);
3. anything those changes introduce, in particular U-7, the WP9.7 RegisterArtefact guard, D-4 and W9-T20.

Unchanged revision 1 content was not re-reviewed.
**Runtime authority:** none. This report edits no other file. Nothing was written to `papers/`, `.apm/`, the vault,
any ARS store, GitHub or Jira, and no `ars` command was run.

**Verdict: REWORK REQUIRED (narrow).** 0 Blocking, 2 Major, 5 Minor, 4 Info. Every revision 1 finding is closed
in substance. The two Majors are new and narrow:
- **N-1:** the WP9.7 RegisterArtefact guard keys on `relative_path` without its `root_id`. That makes it too broad
  and also bypassable.
- **N-2:** the copy-at-a-second-path case of W9-T20 still cannot fail for the right reason. That defect is in the
  correction I prescribed in revision 1's M-4, which the author copied faithfully.

Both are text fixes in 06v. I expect a one-round confirmation once N-1 and N-2 are fixed as proposed.

## 1. Subject and base

| Identity | Value |
|---|---|
| Subject | `implementation/06v-w9-implementation-plan.md`, revision 2 |
| Commit | `db92045f` on `claude/w9-implementation-plan`, parent `b3fe778c` |
| Blob | `0138e17ee2953b2edcba2589681ebf758ac867b3` |
| Reconciliation | `reviews/06v-w9-plan-reconciliation-2026-10-23.md` (same commit) |
| Code base | origin/main `e82f9630` (unchanged since revision 1's review) |

`06v:N` means line N of blob `0138e17e`. All document paths are under `docs/plans/agentic-research-system/`.

## 2. Method

1. `git diff --stat b3fe778c db92045f`: two files, 06v (rewritten) and the reconciliation. I read the reconciliation
   in full and revision 2 in full, then compared each section against the finding it answers.
2. **New citations.** Each was re-read at `e82f9630`:
   - `research_system/command/service.py:4382` (the `RegisterArtefact` branch) and `:6019` (the `CreateTask` branch);
   - `create_task.schema.json:264` and `register_artefact.schema.json:119`;
   - `research_system/store/identity.py:333,355,636,824,857-875`;
   - `research_system/discovery/replay/driver.py:62-65,379-408,667-669`;
   - `research_system/discovery/ledger_integrity.py:38-120`;
   - `research_system/command/lifecycle.py:470-497`;
   - `tools/check_merge_admission.py:703-709`;
   - `research_system/assurance/` (listing).

   I also ran `git diff --stat 4d867d85 e82f9630 -- .research-system/config/foundation.yaml`, which was empty: the
   foundation is unchanged since M2.
3. **U-7.** I traced how a new partition value or predicate would travel through every caller of
   `shared_event_partition`. `Grep` found `discovery/replay/driver.py:59,64,379`, `discovery/runtime.py:2214,2254`,
   `discovery/spec.py:284` and `discovery/spec_assay.py:84`. I also traced it through the generic replay loop
   (`projection/replay.py:1319-1324`, `lifecycle.py:470-497`).
4. **RegisterArtefact guard.** I read the manifest's location fields (`register_artefact.schema.json:113-122`), the
   preparer (`service.py:4382-4410`), and the two places that resolve `root_id`: `artefacts/use_resolver.py:310-317`
   and `discovery/spec_source.py:262-275,304`.
5. **W9-T20.** I traced `load_store_manifest` (`identity.py:857-875`) and `initialize_control_store` (`:767-854`) to see
   which refusal a scratch store and its copy would actually hit.

No test was run; the subject is a plan.

## 3. Closure of revision 1 findings

| Finding | Status | Note |
|---|---|---|
| M-1 shared replay | **Closed in direction** | §2.2 row, WP9.2 predicate, lazy `replay_legacy`, lock, mixed-ledger test with a negative control. U-7's confinement rule is incomplete (n-1). |
| M-2 runtime-binding rows | **Closed** | §2.2 row, the §2.3 consequence, D-4 per package |
| M-3 successor seams | **Closed in direction** | §2.7 maps T8, T10, T11, T12, T16 and T17's W5 clause, with U-2, U-5 and U-6. The T10/T11 guard's key is wrong (N-1). O-34 has no seam (n-4). |
| M-4 Gate 6 identity | **Partly closed** | §2.6 freezes the identity, which is correct; the re-pin consequence is stated. The original-path T20 case now fails for the right reason. The copy case does not (N-2). |
| M-5 §7 restatement; L-1 | **Closed** | §7 now points to W9 §4.5, W9 §8.5 and the 04-plan conditions as operative, and adds only deltas. L-1 never writes `main` or the vault. L-4a, L-4, L-5 and the post-batch S-014 step are added. |
| M-6 detector registry and key | **Closed** | A committed registration manifest; records keyed by PR plus old and new blobs; a fixture registry. A residual window is noted as I-3. |
| M-7 missing obligations | **Closed** | O-32 to O-38 are present. O-32's detector rule is too wide (n-5). |
| M-8 baseline timing | **Closed** | D-7 and L-0b. One sequencing inconsistency remains (n-3). |
| m-1 to m-13 | **Closed** | All thirteen are in the text where the reconciliation says. I checked each: m-4's four corrected citations resolve, m-5's three-package mapping appears in §4, and m-13's not-activated test is in WP9.1. |

## 4. New findings

### Major

#### N-1. The RegisterArtefact guard keys on `relative_path` alone, so it is both too broad and bypassable

- **Claim.** WP9.7 (06v:487-492) and §2.7 (06v:128-129) refuse a `manifest.relative_path` that "is a
  manifest-registered legacy file", "falls under `results/` outside `results/ars/`", or "matches … a restricted
  pattern (`*.pkl`, `*.csv`, null caches)". A relative path has no meaning without its root. The guard does not name
  the `root_id`, and different producers in one store declare different roots.
- **Evidence.**
  - The artefact manifest locates content by the pair `root_id` + `relative_path`
    (`register_artefact.schema.json:113-122`: "Location declared root ID", "Location relative path/URI").
  - Producers already use non-repository roots. The SPEC-01 source documents are registered with `root_id: "control"`
    and `relative_path: "objects/…"` (`discovery/spec_source.py:270,304`).
  - The use resolver reads content by the pair (`artefacts/use_resolver.py:310-314`).
  - `RegisterArtefact` stores no bytes. Its preparer checks only identity, authority and stream state
    (`service.py:4382-4410`).
- **Failure scenarios.**
  - **Too broad.** An artefact under some other declared root, such as an external benchmark checkout or a
    workspace, whose path happens to begin with `results/` is refused although it is not the repository's
    `results/`. The blanket `*.csv` rule also refuses non-restricted CSVs from ARS-native work in the same store, for
    example eval tables or SPEC-style public-data outputs, if that work runs there.
  - **Bypassable.** A producer declares a root that sits inside `results/` (or `PROJ_ROOT`) and passes
    `trajectory_tda_integration/…`, or passes a path containing `..`. The guard sees no `results/` prefix, and the
    legacy write or restricted registration goes through.
  - **Unimplementable as stated.** "Null caches" is not a path pattern. There is nothing for the guard to match.
- **Impact.** Validity of W9-T10 and W9-T11. Operations: false refusals of non-W9 work in a shared store.
- **Disposition.** Fix now.
- **Required change.** Replace the guard text in WP9.7 and §2.7 with:

  > The guard resolves `root_id` to its registered physical root and normalizes the joined path, refusing any `..`,
  > absolute or alias form. It refuses when:
  > - (a) the resolved path is a manifest-registered legacy file;
  > - (b) the resolved root is a registered TDL code root and the path is under `results/` but not under
  >   `results/ars/`;
  > - (c) the resolved path equals a registered `restricted_untracked_file`, or lies under `PROJ_ROOT`'s restricted
  >   area;
  > - (d) the file suffix is in an explicit, owner-accepted restricted-suffix list (W9 §5.4 names `*.csv` and
  >   `*.pkl`), on every root.
  >
  > Rule (d) applies to every producer in the store, because W9-T11 says "on every path".

  Add **D-9**, so that Stephen accepts the suffix list and knows it binds non-W9 work in the Gate 7 store. Replace
  "null caches" with the registered restricted identities. Add negative controls:
  - a root-inside-`results/` registration;
  - a `..` path;
  - a non-`results/` path under a non-code root, which must **not** fire.
- **Affects.** §2.7, WP9.7, O-22, O-23, W9-T10, W9-T11, D-6.

#### N-2. The W9-T20 copy case is refused by binding validation before the W9 guard runs

- **Claim.** WP9.2 reads the manifest "through `load_store_manifest` (`identity.py:857`)" and refuses on the frozen
  `store_identity` (06v:333-337). W9-T20 runs "plus a copy at a second path" and "asserts the W9 guard's own reason
  code" (06v:225). For the copy, the second requirement cannot hold.
- **Evidence.**
  - `load_store_manifest` raises `IntegrityError("store control-root binding mismatch")` when the manifest's
    `control_root` differs from the resolved path (`identity.py:867-868`). It then validates the external witness and
    the restore binding (`:869-874`). A byte copy at a second path fails there, before any W9 code runs.
  - A scratch store also cannot be given the frozen identity through the public initializer.
    `initialize_control_store` mints `store_identity` with `secrets.token_hex(32)` (`identity.py:824`).
- **Failure scenario.** The copy case either fails its reason-code assertion, which triggers the §8 stop rule for a
  plan defect, or it is weakened to "refused for some reason". That reintroduces the vacuous control that M-4 was
  meant to remove.
- **Origin.** This defect is in the correction I prescribed in revision 1's M-4 ("The refusal reads it through
  `load_store_manifest`" and "It also runs on a copy of that store at a second path"). The author applied it as
  written. That is the correlated-error path that observation
  2026-10-22-reviewer-prescribed-identifiers-copied-unverified describes, and here it affects a mechanism, not an
  identifier.
- **Disposition.** Fix now.
- **Required change.**
  - WP9.2: "The guard first reads the manifest with `load_store_manifest_unbound` (`identity.py:636`) and refuses
    with its own reason code if `store_identity` equals the frozen §2.6 value. Only then does it bind through
    `load_store_manifest` (`:857`)."
  - W9-T20: "The fixture builds the scratch store's manifest and origin witness with the frozen `store_identity`
    through `build_store_origin_witness` and `persist_store_origin_witness` (`identity.py:333,355`) under a test
    foundation, never by patching the guard. Both cases (the original path, and a byte copy at a second path) assert
    the W9 reason code. A third case, a store with a different identity, must pass the guard."
- **Affects.** WP9.2, §4 (W9-T20), O-2.

### Minor

- **n-1. U-7's confinement rule omits the Discovery replay's per-partition dispatch.**
  - `replay_discovery` dispatches on the partition value: `artefact`, `operational`, `control` and `context` each
    `continue`, and anything else falls through to `REDUCERS.get(event_type)` and raises "unsupported Discovery
    event" (`driver.py:379-408,667-669`).
  - A new `legacy` partition therefore needs one more `continue` branch in `driver.py`, a third file that U-7 and
    WP9.2 (06v:147, 311-318) do not name. Read literally, the §8 stop rule would fire on that necessary edit.
  - The alternative is to reuse an existing value to stay "confined", for example `context`. That would silently
    enrol W9 events in the shared-projection positions (`driver.py:62-65`).
  - **Required change.** U-7 and WP9.2 name `driver.py`'s dispatch, at one `continue` branch, as in scope and forbid
    reusing an existing partition value. Add a test that every partition consumer leaves W9 events out of its
    operational or artefact filters: `runtime.py:2214,2254`, `spec.py:284` and `spec_assay.py:84`.
  - The generic loop is fine. For a W9 event, `_validate_active_lifecycle_binding` returns early because
    `validate_exact_lifecycle_envelope` gives `None` (`lifecycle.py:494-497`). `_validate_persisted_event_envelopes`
    accepts W9 events once their command rows exist (`ledger_integrity.py:84-104`).
- **n-2. D-4 is workable with two additions.**
  - **(a) Serialize the packages that add commands.** Each one rewrites the same census digest and 06h manifest,
    and the merge queue squashes onto the current main (`check_merge_admission.py:703-709`). Two such PRs in
    parallel make one of the re-accepted byte sets stale. Re-acceptance is of the bytes in the merge-queue entry, and
    any rebase needs a re-look.
  - **(b) Add the T2 manifest's validator seals.** If a tree ID changes, `wp6_2_t2_expectations.py` is edited, and
    its seal in `.research-system/contracts/wp6-2-t2-schema-identities.yaml` changes with it, as P-059 recorded. Add
    the seals to D-4's byte list.
  - Otherwise, per-package re-acceptance at about four PRs, with a register entry each, is proportionate.
- **n-3. D-7 and L-0b contradict each other on timing.** D-7 (06v:508) says the export can be taken "before any
  package lands … under the WP9.0 segmentation contract", but WP9.0 is a package. Either D-7 adopts the segmentation
  contract as a document reviewed with the export, or L-0b waits for WP9.0. Pick one.
- **n-4. O-34 (use-time re-hash of an adopted whole-file input) has no seam.** The artefact use resolver already
  re-hashes at use (`use_resolver.py:313-317`), but N-1's rule (d) refuses registering restricted files as
  artefacts. An adopted restricted input therefore cannot reach the successor Task through that path. Add a §2.7 row
  and a U entry naming where the Task reads and re-hashes it, for example the Task's `source_import_refs` resolved
  against the adoption record.
- **n-5. Detector rule 3 (O-32) flags every change to a shared enforcement surface.**
  - That includes the writes W9 §4.3 allows: ARS reviewed PRs plus a §4.2(b) owner note (W9:185-186).
  - The detector should fail only on a change without the note. Every such change, with or without the note, should
    emit the re-observation requirement.
  - Name how the store learns of it: a recorded command, or the batch checklist. WP9.3's "re-observation is marked
    required" (06v:388) has no input.

### Info

- **I-1. New citations verified.** Every new citation resolves:
  - `service.py:4382` (`RegisterArtefact`) and `:6019` (`CreateTask`);
  - `create_task.schema.json:264` and `register_artefact.schema.json:119`;
  - `identity.py:824,857`;
  - `driver.py:396-400`;
  - `check_merge_admission.py:703-709`;
  - `research_system/assurance/resolver.py`, which exists.

  The foundation is unchanged from M2 `4d867d85` to `e82f9630`, so §2.6's frozen values are the M2 values.
- **I-2. D-1's project-ID reuse is sound.** The refusal keys on `store_identity`. The origin witness path depends on
  the initial control root, so the two stores' witnesses cannot collide. A grant is activated per store, as an event
  in that store's ledger.
- **I-3. Registration-manifest lag.** Between a store registration and the merge of its committed manifest export,
  detector rule 1 cannot see the newly registered file. The acceptance-time re-hash (O-33) bounds the effect. Either
  export the manifest in the same batch before the first observation, or record the window as a known limit.
- **I-4. Known limit, not a finding.** The same model family wrote and reviewed this, and this is the same reviewer
  across both rounds. N-2 shows the cost: a reviewer's prescribed mechanism carried an error the author had no reason
  to re-derive.

## 5. Owner decisions in revision 2

| ID | Disposition |
|---|---|
| D-1 | **Accept.** Specifics complete; I-2. |
| D-2 | **Accept.** Conditions written in. n-1 tightens U-7. |
| D-3 | **Accept.** |
| D-4 | **Accept with n-2** (serialize command-adding packages; add the T2 seals). |
| D-5 | **Accept.** |
| D-6 | **Accept.** |
| D-7 | **Accept, after n-3 is resolved.** |
| D-8 | **Accept** as a conditional decision, taken only if U-3 fails. |
| D-9 (proposed, N-1) | **For Stephen:** the restricted-suffix list for the RegisterArtefact guard, and its reach over all producers in the Gate 7 store. |

## 6. Revision plan

- **Author:** N-1 and N-2 as proposed; n-1 to n-5.
- **Owner:** D-9.
- **Confirmation scope:** the WP9.2 guard text, W9-T20, the WP9.7 and §2.7 guard text, U-7, D-4, D-7 and O-32.

## 7. Change log

- 2026-10-23: re-review written at `db92045f` (blob `0138e17e`). No other file was edited.
