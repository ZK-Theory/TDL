# WP9.3-2: the closed-reference acceptance (LR-016 to LR-020), the derived ownership list, the export recheck and the `.apm/` inventories

**Date:** 2026-11-11<br>
**Status:** Revision 1, merged as `baea2c13` (PR #432, head `bc47fea8`) and accepted (P-084). The independent review (`reviews/wp9-3-2-review-b98515c6-2026-11-11.md`) gave accept at the
merged tree in its addendum, and its one follow-up, m-5, merged as `80baa4a9` (PR #434). P-084 records Q1 to Q3, the §4
readings, the later-pin checklist line and WP9.3's completion.<br>
**Package:** 06v WP9.3, the second and last WP9.3 PR (owner point A; P-081 item 1, as P-082 item 5 amends it).<br>
**Authority:**
- P-080; P-081 with all its amendments;
- P-082 items 3, 5 and 6;
- P-083 items 3 to 6, with item 5 as corrected on 2026-11-11 (Stephen, in chat: "Yes, revise both", on CodeRabbit's
  comment on PR #430);
- the WP9.3 design note, revision 14 (`2d9aeddc`): §2.3, §6.1, §6.2, §7.2, §10, §11, §12, §13, §15, §16 and §17;
- the WP9.3-1b review's addendum, n-1, n-3 and n-4 (`reviews/wp9-3-1b-review-649d0698-2026-11-10.md` §A.3);
- Stephen's answers to the WP9.3-2 plan's Q1 to Q3 (in chat, 2026-11-11: "Partial list + show", then "Yes, as
  recommended" for all three, relayed by the Gate 7 handover session).<br>

**Base:** `origin/main` at `b6ecfdfc` (PR #430, P-083). P-082 item 5 and P-083 item 6 place WP9.3-2's base at
`fbb99ce0` (PR #429). `b6ecfdfc` descends from it through two commits: `23779c98` (PR #431, SYS) changes only
`tests/tools/test_research_system_ci_tools.py`, and `b6ecfdfc` (PR #430) changes only docs, with no file under
`research_system/` in either.<br>
**Boundary:** P-080's, as P-081 item 10 extends it. Production changes are confined to `research_system/cli.py` and
`research_system/legacy/`. `store/`, `command/`, `discovery/`, `projection/`, `authority.py`, `schema_registry.py`, the
schema trees and `tools/w9_segmentation.py` (blob `43e1454d`, P-068) are unchanged (§5).<br>
**Not authorized (P-080):**
- WP9.4 to WP9.7;
- live operations L-0 to L-5, including the D-7 baseline export;
- a real store, or genesis or a grant on one;
- any legacy write.

Every store in these tests is a scratch store under `tmp_path`. Every source, log and `.apm/` tree is synthetic, in a
scratch Git repository under `tmp_path`.

## 1. What landed

| Source | Code |
|---|---|
| P-083 items 5 and 6 (n-1), as corrected | `cli._foundation_binding_check` reads "never bound" from durable store evidence. Under the writer lock, an absent pointer is "no current binding" only when no `objects/binding-repair/` object exists and no binding was loaded before binding. Otherwise it refuses with the fixed message, ending "its binding pointer is absent". The decision is deferred to the lock, so a command that starts during a healthy advance loads the published pointer |
| P-083 item 6 (n-3) | The `CommandService` construction census follows `functools.partial` (counting only a check the `partial` itself binds), `getattr` and `operator.attrgetter` with a constant name, and `globals()`, `vars()` and `__dict__` subscripts. A backstop fails any production string literal `"CommandService"` outside an annotation |
| P-083 item 6 (n-4) | The re-check probe becomes `test_each_cli_writer_refuses_an_unloadable_named_binding_before_it_reads_or_builds`, over the five handlers, with a positive axis |
| Note §2.3, §15; owner point F | LR-016 to LR-020 are routed. The partition is 19 routed and 42 deferred, pinned by the route test |
| Note §6.2 LR-016, §10.1, §10.2, §10.5; owner points E, G, K′ | `reducers.check_acceptance`, `derive_ownership` and `_reserve_ownership`: the batch rules, `pilot_promotion`, `git_commit` anchors only, no null change list, one whole-file item per registration, and the derived ownership list, reserved and stored with the proposal |
| Note §6.2 LR-017 to LR-019; §5.5 | The request, verdict and Decision rules of WP9.3-1 through the extended field tables, plus: LR-017's reviewer observed no item of the batch |
| Note §6.1, §6.2 LR-020, §10.6; P-082 item 3 | G5 with `W9:LR-020`, the batch rules again, the emitted ownership records equal to the stored list and to the list recomputed there, each on its own stream at version 1 with the acceptance's copied refs, each taking its reservation |
| Note §7.2 (O-33, W9-T6), §10.3 (W9-T16), §10.4 (O-32) | `legacy/acceptance.py`: the window (each item's source re-read, and its frozen copy), the anchors, the change list and the detector controls, at LR-016 and again at LR-020, with the window re-run at commit |
| Note §10.4, §11.1; paths addendum row 27 | `evidence.SHARED_SURFACE_CHANGES` (`.research-system/evidence/w9/shared-surface-changes.json`), format `w9-shared-surface-changes/1`, and `require_change_list` |
| Note §12.2; D-7; review M-4 | `evidence.require_cl_export` (format `w9-cl-export/1`), `legacy/export_recheck.py`, and `ars legacy export recheck` |
| Note §12.3, §12.4 (O-19, O-36, W9-T18) | `legacy/apm_inventory.py`, and `ars legacy apm-inventory bus` and `files` |
| Note §12.1 (O9); Q1 | `inventory.build_acceptance_batch` and `ars legacy inventory batch` |
| Gate 7+ intake §2 rows 36 and 37 | `test_w9_pilot_promotion_table.py` and `test_w9_precondition_fields.py` |
| Found by the batch-mode test | `ars legacy show` renders projection entries as JSON. It failed on every proposal, whose lapse time is a datetime |

## 2. Fixed values

- **n-1's refusal:** `"<command> refused: the store has a current binding this checkout cannot load: its binding
  pointer is absent"`.
- **Batch limit:** `MAX_BATCH_ITEMS = 20`. LR-020's fixtures: `UNCONDITIONAL_FIXTURES = ("F-018", "F-023", "F-037",
  "S-014")` and `CONDITIONAL_FIXTURES = ("F-017", "S-005", "F-038")`, bound to the parsed catalogue row by
  `test_w9_pilot_promotion_table.py`.
- **Ownership record ID:** `derived_id("obj", "w9-ownership:<acceptance ID>:<registration ID>", ms(<acceptance
  created_at>))` (`records.ownership_record_id`). The other fields are as §10.5 states, plus R6.
- **Formats:**
  - `w9-shared-surface-changes/1`: `{"format", "entries": [{"merge_commit", "surface", "affected_registrations":
    [{"root_kind", "root_id", "normalized_path"}]}]}`;
  - `w9-cl-export/1`: `{"format", "selector": {"selector_kind": "computational_log_entry", "region": {"first_line",
    "last_line"}}, "segmentation": <the reference tool's segment() output>, "read": {"started_at", "ended_at",
    "path_form", "limits"}, "retained_copy": {"repository_path", "git_blob", "sha256", "byte_length"},
    "classifications": [{"ordinal", "class"}], "producer": {"repository_path", "git_blob"}}`;
  - `w9-cl-export-recheck/1`, `w9-apm-bus-inventory/1`, `w9-apm-file-inventory/1` and `w9-apm-closure-map/1` (R9).
- **The admitted export producer:** `tools/w9_segmentation.py` at blob `43e1454de09b61e274954c42b21d6ae533857a24`.
- **CLI:**
  - `ars legacy export recheck --repository-root --git-commit --export --vault-root --output`;
  - `ars legacy apm-inventory bus --apm-root --vault-root --output`;
  - `ars legacy apm-inventory files --repository-root --git-commit --closure-map --vault-root --output`;
  - `ars legacy inventory batch --batch --vault-root --output`.

  Each opens no store and refuses its output under `.apm/`, under the vault, inside a store, inside a repository it
  reads, or over an existing file. `recheck` and `files` exit 1 on a void export or a blocking inventory.

## 3. The governing rulings

- **P-083 item 5, as corrected (2026-11-11):** "WP9.3-2 carries n-1's hardening: 'never bound' is read from durable
  store evidence, not from the pointer alone … The line is dropped when that hardening merges, not on a check that
  covers only a binding loaded before the lock."
- **P-083 item 6:** "Carried to WP9.3-2: n-1 (item 5); n-3 …; n-4 …; O9 (item 3)."
- **P-082 item 3:** the resolution's `governing_evidence_refs` carry `W9:LR-020` in WP9.3-2.
- **P-081 item 5 (owner point E):** LR-016's list is read as "the proposal determines"; replay derives it, stores it at
  LR-016, and requires it at LR-020; at most one whole-file item per registration.
- **The plan's Q1 to Q3 (Stephen, 2026-11-11):** Q1, batch mode prints the fixed parts and `ars legacy show` the full
  list; Q2, a `pilot_promotion` fixture outside LR-020's seven is refused; Q3, the paths addendum's export row cites
  `w9-cl-export/1`, as a dated amendment.

**For Stephen after the merge:** P-083 item 5 drops the later-pin checklist line ("No ARS CLI writer ran from the old
checkout after the advance, and no advance on the store ended without publishing its new binding") once this hardening
merges. Dropping it is your call, in the merge entry.

## 4. Readings the reviewer should check

1. **R1 (n-1).** "Never bound" means no pointer and no binding objects, decided under the lock. P-082's own authority
   line reads "skip the recheck only for a store that was never bound". Every repair and advance writes its object
   before it touches the pointer (`store/binding_service.py:1233` before `:1307`; `:1776` before `:1877`). Store init
   creates `objects/` but not `objects/binding-repair/` (`store/layout.py:10`, `:59`). An empty
   `objects/binding-repair/` directory therefore counts as bound.
2. **R2 (n-3).** A class name computed at run time (`"Command" + "Service"`, or a name read from data) cannot be seen
   by an AST census. It joins note §18's census-reach review question, widened to `CommandService`.
3. **R3 (§10.3).** "The commit adds or changes a file" is read against the commit's first parent, or against the empty
   tree for a root commit.
4. **R4 (§10.4).** "Names the list's commit and blob, and must equal the list at `git_head`" is read as follows: the
   blob is the list's blob at `git_head`, and the named commit is an ancestor of `git_head` (or `git_head` itself) that
   holds that blob.
5. **R5 (§10.4).** A registration is "among an entry's affected results" by its `root_kind`, `root_id` and
   `normalized_path`, the registration manifest's key.
6. **R6 (§10.5).** The ownership record's fields that §10.5 leaves implicit are `schema_version` `1.0.0`,
   `record_revision` 1, `supersedes_revision` null and the acceptance's `project_id`. The list is in item order.
7. **R7 (§12.2).** The export's `segmentation` member is the reference tool's `segment()` output, verbatim, and its
   other members are assembled at L-0b. L-0b is not authorized, and the reference tool has no export mode. The recheck
   exits 1 on a void export. It refuses a producer that is the runtime segmenter, and any producer but blob
   `43e1454d`.
8. **R8 (§5.5).** A batch is the analyst's own proposal, as a path registration is, so §5.5's analyst-creator rule
   (which names observers and membership authors) does not refuse the batch's analyst as its requester. LR-017's
   reviewer exclusions (the creator, the analyst, and every item's observer) apply.
9. **R9 (§12.4).** The closure map is an operator-supplied JSON, `w9-apm-closure-map/1`. Its records are recomputed at
   their content hash, and in v1 there is no store record (P-071 item 4).
10. **R10 (§7.2).** At LR-016 and LR-020 a `git_tracked` item's re-read is compared by location and bytes, not by
    `git_commit`. A later binding head moves the commit but not the blob, and §7.2 says the recorded bytes "cannot
    move". Comparing the commit would refuse every acceptance after any commit.
11. **Q1's reading of §12.1.** The builder prints the derived list's fixed parts. Each record's ID, `created_at` and
    hash are marked "assigned at LR-016", because the ID's timestamp is the proposal's `created_at`, set at submit, and
    the tool opens no store. `ars legacy show` prints the stored list after LR-016.
12. **Q2.** Refusing a fixture outside LR-020's seven is stricter than §10.2's text, which states only the four
    unconditional fixtures.
13. **The intake-row tests.** The fixture table is owned and built from W9 §12.3 by category, and checked against the
    parsed catalogue. The precondition table maps 13 matching preconditions, plus LR-016's exception.
14. **R11 (§10.1, CodeRabbit on #432).** "The latest for its source and selector" compares a `json_family_set`
    selector's `family_names` as a set, as `_check_selector` and `_whole_file` already read them. Every other selector
    field compares as recorded.
15. **R12 (D-7; addendum row 28, CodeRabbit on #432).** "In the evidence area" is enforced: the export's retained copy
    must be a file under `.research-system/evidence/w9/`, named in normal POSIX form.

**Departure, for the merge entry.** The W9 paths addendum (`implementation/06v-addendum-2026-11-10-w9-paths.md`) gets a
dated amendment, which changes an addendum's text:
- row 28's "Format fixed by" column now also cites `w9-cl-export/1` (Q3). Its old wording, "the segmentation contract
  (P-068) and note §11.3", is quoted in the amendment;
- row 27's file name is fixed, as the row asked WP9.3-2 to do;
- the table's `evidence.py` line numbers are re-cited.

## 5. No D-4

`git diff --stat b6ecfdfc <head>` over the protected paths is empty:
- `.research-system/`, `research_system/schema_registry.py` and `research_system/authority.py`;
- `research_system/store/`, `command/`, `discovery/` and `projection/`;
- `tools/w9_segmentation.py` (blob `43e1454d`);
- `tests/research_system/unit/test_schema_registry.py` and `tests/research_system/smoke/`.

The 06h manifest is blob `4c895042` and the smoke test blob `559d684a`, as P-082 accepted. The census stays at 273
rows (§7). No command type, binding row, schema or append site is added.

## 6. Tests

| File | What it shows |
|---|---|
| `integration/test_w9_wp9_3_writers.py` (n-1, n-4) | The n-1 probe inverted, a fresh process, an empty object directory, a pointer published before the lock, the never-bound no-op, the directory pin; each of the five writers refusing through its handler, with a positive axis |
| `contracts/test_w9_wp9_3_censuses.py` (n-3) | Eight fixture forms (`partial` unchecked, checked and checked-on-call, `getattr`, `attrgetter`, `globals()`, `vars()`, `__dict__`), the string backstop and its positive control |
| `unit/test_w9_evidence_acceptance.py` | The change list (absent, null, wrong blob, non-ancestor commit, commit not holding the list, five malformed forms) and the export format (fourteen malformed forms), with exports built by the reference tool |
| `integration/test_w9_wp9_3_2_replay.py` | 38 forged-ledger cases: the positive flow through every public replay; the derivation's determinism and distinctness; each batch, `pilot_promotion`, anchor, change-list, LR-017 to LR-019 and LR-020 control; two batches sharing an item; the reserved ownership ID |
| `integration/test_w9_wp9_3_2_runtime.py` | 21 cases through `submit`: the accepted batch; W9-C11 retries of every step; the role rules; W9-T6 at LR-016 and LR-020; both O-33 gaps, untracked and restricted; the deleted and altered frozen copy; W9-T16's three controls; R10; O-32's five cases. Each refusal leaves the ledger and the control root byte-identical |
| `unit/test_w9_export_recheck.py` | 17 cases: reproduction, a one-byte change, tampered rows, suppressed anchors and facts, both producer refusals, the tool reading Git and never the working tree, each forbidden output, the argument guards |
| `unit/test_w9_apm_inventory.py` | 24 cases: the universe, the exact bijection, a missing, extra or doubled file, a missing or extra item, a blocker row left, a record at another hash, the bus inventory, a second hard link, the tools' outputs and their guards |
| `integration/test_w9_wp9_3_2_batch_build.py` | A CLI-built proposal admitted at a real LR-016, its stored list agreeing with the printed parts, `ars legacy show` printing it read-only, and the refusals |
| `contracts/test_w9_pilot_promotion_table.py`, `contracts/test_w9_precondition_fields.py` | Intake rows 36 and 37, each with its control |
| `contracts/test_w9_legacy_routes.py`, `integration/test_w9_legacy_replay.py` | The partition re-pinned at 19 and 42. The WP9.2-era bare LR-020 test is retired, and its assertion moved to the positive flow. LR-016 now reaches its schema check |

## 7. Verification

Run on the operator machine (Windows, Python 3.13), on 2026-11-11.

- **Regression:** 52 files, one process, at `70605973` (before the weights commit `9b673247`), gave 1,829 passed, 1
  skipped and 1 failed, in 4,297 s (71 min 37 s).
  - The skip is the existing `rfc3339-validator absent` skip.
  - The failure was `test_recorded_durations_are_positive_and_cover_most_files`. The eight new files had no shard
    weight, so coverage fell below 90%. The weights are added (`tools/research_system_durations.json`), and the
    `ci-tools` file then gave 61 passed.
  - The files were every W9 file, the W11 group, the CLI-submit files, every file that drives the six checked
    writers, the 06h smoke test, `test_schema_registry.py`, `ci-tools` and `test_w9_segmentation.py`.
- **After the regression,** five controls were added for the mutations below (an empty change-list surface, a
  registration not `legacy_owned`, the commit-time re-read, the copy's blob, and n-1's loaded limb alone). Their files
  gave 47 passed, and the writers' n-1 and n-4 tests 17 passed.
- **Mutation script** (scratch, not committed, as WP9.3-1's and WP9.3-1b's were; note §17): **69 of 69** single-guard
  mutations were caught by an executed test failure, each asserting its own message. Each file was restored byte for
  byte after every mutation.
  - The first pass caught 64 of 69. One `r-anchor-kind` "catch" was a syntax error, a broken mutation, which was
    fixed. Four guards were missed: the change-list `surface`, the derivation's mode test, the commit-time re-read,
    and the export copy's blob.
  - Each of the four got its own control above, and the five were re-run, 5 of 5 caught.
  - The mutations cover n-1 (three), n-3 (six), the evidence formats (nine), the LR-016 to LR-019 replay checks
    (twenty), LR-020 (six), the environment checks (nine), the export recheck (five), the `.apm/` inventories (nine)
    and batch mode (two).
- **Runtime evidence for the open escalation (P-082, P-083 "Not decided here"):** the regression took 71 min 37 s for
  52 files, against WP9.3-1b's 52 min 47 s for 34 files.
  - The new files cost about 4.4 min in all: the runtime file 215 s, batch build 35 s, and each of the others under
    10 s.
  - A `submit`-level acceptance case costs about 20 s, of which 12 s is the scratch store's setup. No new case uses the
    v1.2 advance fixture.
  - The rest of the growth is the wider file selection: the writer driver files 1b's re-check ran separately.
- **Ruff:** check and format are clean on every changed file. Pre-commit ran on every commit.

## 8. Obligations and test gaps

- **For Stephen:** dropping the later-pin checklist line (§3).
- **For WP9.3-2's independent review** (a separate session, P-081 item 6):
  - re-verify the genesis path at this head, since guard 8's input changes (owner point F);
  - check R1 against an absent-final crash on a real anchor transaction;
  - check the plan's T5 (LR-016 to LR-019 at replay: the batch rules, `pilot_promotion`, the anchors' kind, the
    change list's presence, the ownership derivation and its reservation) and T7 (LR-020: G5, the stored ownership
    list emitted exactly and recomputed, and the window re-read at resolution) against note §10;
  - check the tools' write-nothing claims.
- **Known limits carried, not changed:**
  - a computed class name escapes the census (R2);
  - the S-014 freshness check is Stephen's at resolution (§10.2);
  - frozen-copy retention (§7.2);
  - L-0b, the export's producer, is not authorized, so the recheck has run only on synthetic logs.
- **Test gaps:** none known beyond the above. The batch limit's guard is reached with the bound lowered in the test,
  not with 21 observations, and the real value is pinned separately.

## 9. Review dispositions

The WP9.3-1b review's addendum (§A.3):
- **n-1:** fixed (§1, R1);
- **n-2:** confirmed by P-083 item 4, unchanged;
- **n-3:** fixed, with R2's residue;
- **n-4:** fixed;
- **n-5:** fixed in #429.

O9 (P-083 item 3) is done under Q1's reading.

## 10. CodeRabbit on #432, and the independent review's further fixes (2026-11-11)

CodeRabbit left 14 inline findings at `b98515c6`. WP9.3-2's independent review
(`reviews/wp9-3-2-review-b98515c6-2026-11-11.md`, on `review/w9-wp9-3-2`) reached accept with required changes:
0 Blocking, 0 Major, 4 Minor (m-1 to m-4), 8 Info and no D-4. Stephen sent its fixes beyond CodeRabbit's threads for
the same push. Each finding was checked against the code, and each holds. None changes a command type, a protected
path, a register entry, a decision or an accepted text. The "Review" column names the review finding that shares the
thread.

| # | Review | Where | Finding | Fix | Control |
|---|---|---|---|---|---|
| 1 | m-3 | `acceptance.py`, `_introduced_blobs` | A failed parent lookup was read as a root commit, so the whole inherited tree passed W9-T16 | Parents read with `rev-list --parents -n 1`; a failed lookup refuses | `test_a_failed_parent_lookup_refuses_and_is_never_read_as_a_root_commit`, plus root and inherited-bytes controls |
| 2 | m-4 | `apm_inventory.py`, `_walk_files` | `os.walk` skips an unlistable directory, so an inventory could be partial | `onerror` raises | `test_a_directory_that_cannot_be_listed_is_refused` (universe, bus) |
| 3 | m-4 | `apm_inventory.py`, roots | `os.walk` follows a linked start directory | `.apm/`, `memory/`, each stage and the bus are refused when linked | `test_a_linked_stage_bus_or_memory_root_is_refused_before_it_is_listed` (stage, bus, memory) |
| 4 | m-4 | `apm_inventory.py`, observations | Only the inventory ID and ordinal were compared | The whole inventory ref, the selector kind, the anchor and the raw row hash, as replay checks them | `test_an_observation_whose_selector_differs_from_its_item_row_blocks` (five fields) |
| 5 | m-4 | `apm_inventory.py`, non-import | `"record": null` placed its files | `record` must be `{kind, sha256}`, a non-empty kind and a SHA-256 | `test_a_non_import_entry_without_its_record_is_refused` (five forms) |
| 6 | none | `evidence.py`, change list | A null or empty `normalized_path` matched nothing, so freshness never ran | Each affected-registration member is a non-empty string | `test_a_malformed_change_list_is_refused` (null and empty path) |
| 7 | none | `evidence.py`, `_utc` | `2026-02-30T00:00:00Z` raised `ValueError` past the controlled refusal | Returns `None`, so the format refusal fires | `test_a_malformed_export_is_refused[read-calendar]` |
| 8 | none | `evidence.py`, retained copy | Any repository path was accepted (R12) | The copy must be under the evidence area | `test_a_malformed_export_is_refused` (outside, `..`, the directory itself) |
| 9 | m-2 | `inventory.py`, batch mode | A `json_family_set` item with no membership record was previewed as transitioning nothing | Refused whenever the selector is `json_family_set` | `test_batch_mode_refuses_a_family_set_with_no_membership_record`, with a positive control |
| 10 | m-2 | `inventory.py`, batch mode | Membership and registration links were compared by ID only | ID, revision and content hash, as §4.4 resolves a ref | `test_batch_mode_refuses_a_membership_record_at_another_hash_under_the_same_id`, and the registration twin |
| 11 | i-1 | `reducers.py`, `_batch_rules` | Family-set selectors compared with family order significant (R11) | `_selector_key` compares family names as a set | `test_lr016_compares_family_set_selectors_as_sets` |
| 12 | m-1 | census, aliases | `alias = factory` lost the partial's bound check | The alias inherits it | `checked-partial-alias`, `unchecked-partial-alias` |
| 13 | m-1 | census, overrides | `factory(binding_check=None)` was counted as checked | A constant `binding_check=` or a `**` mapping at invocation counts as unchecked | `named-partial-none-override`, `inline-partial-none-override`, `partial-splat-override` |
| 14 | none | `unit/test_w9_evidence_acceptance.py` | Four public helpers lacked docstrings | Added | none needed |

**The review's fixes beyond CodeRabbit's threads:**

| Review | Where | Finding | Fix | Control |
|---|---|---|---|---|
| m-1 | census | `from ... import CommandService as Svc`, `from functools import partial as p`, an annotated assignment and a walrus were reported as no construction at all | Import aliases of the class and of `partial` are followed; `AnnAssign` and `NamedExpr` bind like an assignment; a called walrus is a construction | `import-alias`, `import-alias-checked`, `partial-import-alias`, `annotated-partial`, `walrus`, `walrus-called`. The walrus is handled, so no new limit joins R2 |
| m-3 | `acceptance.py`, `_introduced_blobs` | In a `--depth 1` clone Git lists the boundary commit with no parents, so row 1's fix alone still read it as a root commit | A shallow repository refuses (`rev-parse --is-shallow-repository`) before any parent lookup | `test_a_shallow_repository_is_refused_before_its_boundary_commit_reads_as_a_root` (a full clone refuses the anchor; the shallow clone refuses as shallow) |
| m-4 | `apm_inventory.py`, roots | A linked `memory` root, beside the stage and bus roots | Already in row 3 | row 3's `memory` case |

The review's Info findings other than i-1 change no code in this round.

**CodeRabbit's second pass, at `4636bc4c`:** three new findings, each checked and each holding.

| Where | Finding | Fix | Control |
|---|---|---|---|
| `apm_inventory.py`, `_walk_files` | `followlinks=False` keeps `os.walk` out of linked directories, but a linked file is still listed and counted as an `.apm/` file | A linked file refuses | `test_a_linked_file_in_a_stage_log_or_the_bus_is_refused` (stage, bus) |
| `apm_inventory.py`, observations | An observation of another registration still counted its row, which replay's §8.2 refuses | The observation's registration must be its inventory's | `test_an_observation_of_another_registration_blocks` |
| census, aliases | `alias = factory` then `alias = CommandService` kept the partial's checked flag | The census is flow-insensitive: a name is a checked partial only if every class-valued binding of it is one | `alias-rebound-to-class`; `partial-rebound-unchecked` is a preservation control |

Red evidence: the three production controls failed against `4636bc4c`'s `apm_inventory.py`. `alias-rebound-to-class`
failed against `4636bc4c`'s census. `partial-rebound-unchecked` passed there, because the old census's last walked
binding happened to win. The rule is conservative: a name rebound from an unchecked to a checked partial is reported
unchecked, and no production construction does that.

**CodeRabbit's third pass, at `26f9af91`:** one finding. The rebinding rule keyed partial bindings by name alone
across the module, so two functions binding the same local name merged their flags and valid code was reported
unchecked. Partial bindings are now keyed by lexical scope, the chain of enclosing defs, classes and lambdas. A call
resolves its name from the innermost scope that gives it a class value. Controls: `same-name-in-two-functions` and
`local-shadows-module-partial`, which both failed against `26f9af91`'s census and pass now. The census file gave 52
passed, its production census included.

**Red evidence.** With the five production files restored from `b98515c6`, the new production controls gave 26 failed
(each by its own assertion or refusal text) and the preservation controls passed. One first draft of finding 4's ref
cases passed on the old code because its ref named a fresh inventory: it was refused by the ID check, not the guard
under test. It was rewritten to change only the revision or the hash, and then failed 5 of 5 on the old code. For the
census, the eleven new fixtures were run against `b98515c6`'s `_service_constructions`: the ten remediation fixtures
failed, and `unchecked-partial-alias`, a preservation control, passed. With the shallow-repository guard alone removed
from the fixed `acceptance.py`, the shallow control failed ("DID NOT RAISE"), so row 1's fix does not cover m-3. All
pass at the new head.

**Green runs** (operator machine, 2026-11-11). After CodeRabbit's fourteen fixes, the thirteen affected files gave 420
passed in 631 s:
- the evidence, export-recheck and `.apm/` inventory units;
- the census;
- batch build;
- both WP9.3 replay files and `test_w9_legacy_replay.py`;
- both WP9.3 runtime files;
- the inventory builder;
- the two intake-row contracts.

After the review's m-1 and m-3 additions, the files those reach gave 137 passed in 273 s: the evidence and
export-recheck units, the census, the WP9.3-2 runtime file and batch build. Ruff check and format are clean on every
changed file.
