# WP9.3-1b: the `ars submit` refusal, the light-inventory builder, LR-011's resolution check, and the review's dispositions

**Date:** 2026-11-10<br>
**Status:** Revision 1, for review. The PR is open for CodeRabbit and needs its own independent review (P-082 item 5).<br>
**Package:** 06v WP9.3. This is the follow-up PR that P-082 item 5 places between WP9.3-1 (`23f8f737`, PR #420) and
WP9.3-2. WP9.3-2 is cut from this PR's merge commit (P-082 item 5, amending P-081 item 1).<br>
**Authority:**
- P-082 items 4 to 6 (Stephen, in chat, 2026-11-10: "Yes, as recommended"), which amend P-081 items 1, 3 and 10;
- the WP9.3 design note, revision 14 (`2d9aeddc`);
- the independent review `reviews/wp9-3-1-review-23f8f737-2026-11-10.md`: M-1, M-2, M-3, m-4 and i-1 to i-6.<br>

**Base:** `main` at `0ea4e489` (PR #426, P-082).<br>
**Boundary:** P-080's, as P-081 item 10 extends it. Production changes are confined to `research_system/cli.py` and
`research_system/legacy/`. Nothing outside them changes: `store/`, `command/`, `discovery/` and `projection/` are
unchanged, and so is `tools/w9_segmentation.py` (blob `43e1454d`, P-068).<br>
**Not authorized (P-080):**
- WP9.4 to WP9.7;
- live operations L-0 to L-5;
- a real store, or genesis or a grant on one;
- any legacy write.

Every store in these tests is a scratch store under `tmp_path`, and every source is a scratch Git repository under
`tmp_path`.

## 1. What landed

| Source | Code |
|---|---|
| P-082 item 4; review M-1 | `cli._foundation_binding_check`: the recheck is skipped only for a store the canonical foundation does not name, or one with **no current binding**. "No current binding" means `control_root/manifests/binding-repair-current.json` is absent (`os.path.lexists`), never a load failure. A named store whose pointer exists must load from this checkout. Otherwise `ars submit` refuses with `ConfigurationError("ars submit refused: the store has a current binding this checkout cannot load: …")` before it builds the ledger or `CommandService`. `ConflictError` refuses as itself |
| P-082 item 5; review M-2; contract §3 | `legacy/segmentation.resolve_first_anchor_after`, an additive function: the first anchor line after `after_line`, and the file's last line. LR-011's `check_resegmentation` requires the declared `resolved_first_line` and `resolved_last_line` to equal it. The `after_line` hash moves into a shared `after_line_sha256`, which gives no hash for a line outside the file instead of indexing past it |
| P-082 item 5; review M-3; note §8.3, §12.1 | `legacy/inventory.py`: `build_light_inventory` (build mode) and `reproduce_light_inventory` (reproduction mode), sharing the resolution and `segment_kwargs` with LR-011 |
| Note §12, §13; §17 "Tools write nothing" | `cli.py`: `ars legacy inventory build` and `ars legacy inventory reproduce`. They open no store, and refuse a forbidden output before any input is read (`legacy/inventory.refuse_tool_output`) |
| Review i-2 | `legacy/replay/reducers._check_observation`: `observed_at` must equal the event's `occurred_at`, and `non_inferences` must be §7.4's fixed strings for the source kind. Replay imports `NON_INFERENCES` from `legacy/reader.py`, where it stays: the reader's module blob is in the importer hash (WP9.3-1 record §2), so the hashed modules and their coverage do not change. An interim commit had moved the constant to `records.py`, and a later commit moves it back |
| Review i-4 | `legacy/identities.NON_W9_ID_FIELDS`: three T2 cost-grant events' `rate_evidence_id` and `zero_cost_authority/subject_id`, as references |

## 2. Fixed values

- **Messages:**
  - "ars submit refused: the store has a current binding this checkout cannot load";
  - "W9 inventory region resolution differs from the first anchor after its after_line";
  - "W9 inventory region cannot be resolved: …";
  - "W9 tool output is under .apm/", "… is under the vault", "… is inside a store", "… is inside the repository it
    reads", "… already exists";
  - "W9 reproduction bytes are not the inventory's source";
  - "W9 observation observed_at is not the event's time";
  - "W9 observation non_inferences are not the fixed strings for its source kind".
- **The anchor line of a resolution:**
  - `heading_section`: a level-k heading no declared structural range suppresses;
  - `computational_log_entry`: a level-2 or level-3 heading starting with a date token, **or with a digit that is not
    one**, since that heading opens an `unparseable_anchor` blocker (§4 item 2).
  - In both cases, exactly the lines that open an item or blocker row under `segment`.
- **The CLI:**
  - `ars legacy inventory build --registration --selector-kind [--heading-level] [--line-range A:B | --after-line N]
    [--structural A:B …] --repository-root --git-head [--vault-root] [--frozen-copy-ref] --observer --project-id
    --output`;
  - `ars legacy inventory reproduce --inventory (--repository-root | --frozen-copy) --output`, which exits 1 when its
    report shows a difference.
- **No D-4** (§5).

## 3. The governing rulings (P-082, 2026-11-10)

- **Item 4 (M-1).** "`ars submit` skips the recheck only for a store that the canonical foundation does not name, or
  that has no current binding; when the foundation names the store and it has a current binding that this checkout
  cannot load, `ars submit` refuses before binding." This amends P-081 item 3 for the eighth time, and replaces the
  WP9.3-1 record's §3 item 3 reading of "tries". **From this PR's merge**, note §9.1's "On WP9.3-1 code the
  `CommandService` recheck refuses it", and §18's refusal of a writer on pre-pin code, hold for generic `ars submit` too.
  The interim later-pin checklist line, "No generic `ars submit` ran from the old checkout after the advance", is
  Stephen's to drop once this merges.
- **Item 5 (M-2, M-3).** The builder and its reproduction mode, the resolution check they share, and item 4's fix. No
  D-4.
- **Item 6 (m-1 to m-3).** These are readings of contract §3. The segmenter's behaviour does not change, and this PR
  changes no existing segmenter function.

## 4. Readings the reviewer should check

1. **i-1. Accepted by Stephen in chat on 2026-11-10 ("Record as reading (Recommended)").** At the instant a W9
   Decision's `expires_at` equals its proposal's lapse time, note §4.6 (open only before the lapse) governs, and the
   resolution is refused. §5.2's "not after `expires_at`" would admit it at that one instant. The code and
   `test_a_lapsed_proposal_cannot_be_resolved` are unchanged, and the test's docstring cites this reading. No accepted
   text changes.
2. **The log-entry anchor includes digit blockers.** P-082 item 5 says "the first non-suppressed anchor line". For
   `computational_log_entry`, a level-2 or level-3 heading that starts with a digit but not a date token opens an
   `unparseable_anchor` blocker row (`segmentation._log_entries`). A resolution that skipped it would drop that blocker,
   which is the harm M-2 names (note §6.2, "so no blocker row is dropped"). So it counts as an anchor line. A property
   test checks, over generated inputs, that the resolved line opens the region's first item or blocker row, and that no
   line between `after_line` and it opens one.
3. **The tools refuse an output inside the repository they read.** Note §12 lists `.apm/`, the vault and a store. A
   file written in the repository would change the input tree, which §17's "Tools write nothing" row forbids, and would
   make the reader's dual Git read refuse. An existing output is also refused, so nothing is overwritten.
4. **`--git-head` is the operator's.** No tool opens a store, so the builder cannot read the binding's `git_head`.
   LR-011's preparer re-reads at the binding's `git_head`, so a proposal built at another head is refused there.
5. **`reproduce --frozen-copy` treats the frozen copy's directory as an input tree.** The frozen copy normally sits in
   a store's evidence area, which the store check already refuses.
6. **O9 deferred.** Note §12.1's "prints the derived ownership list when it builds a batch (§10.5)" belongs to
   WP9.3-2, which owns batches and the ownership list (note §2.3). This PR's builder builds one inventory.
7. **i-3, kept as a reading.** The reader and replay refuse a file named `conventions.md` in any directory and any case,
   outside a `conventions_lock`. That is stricter than §7.1's rule against the repository's `CONVENTIONS.md`, and is
   left so.
8. **i-4, unpatterned fields.** The widened census now catches a field whose pattern admits a W9 ID. It found the two
   T2 references listed in §1, and both are classified. Sixty-nine payload fields named `*_id`, or items of `*_ids`, have
   no pattern at all (for example `request_id` and `session_id` on context-packet events). A schema says nothing about
   what they hold, so no mechanical census can classify them. Their creation sites are not W9-kind aggregates (review
   §7.1 lists every creation site). This is recorded, not mechanized.
9. **m-4 uses the reserved `obj_`, not a reserved `rev_`.** A generic or W11 creation of a reserved `rev_` needs a full
   artefact or candidate lifecycle (i-6). The control's foreign event is a generic `CreateScopeDefinition` on W9's
   reserved `obj_`, written by the real writer with its W9 guard monkeypatched off. It meets the same fixed-identity
   check. A second finding: even with the guard off, the generic writer's receipt step runs the public replay after the
   append and refuses. So a forged ledger through the real writer is still caught one step later, though the event is
   already appended.
10. **The reviewer's committed probe now fails, as intended.**
    `reviews/wp9-3-1-review-artifacts/test_review_probes.py::test_m2_a_wrong_resolution_of_first_anchor_after_is_admitted`
    asserts the M-2 defect, and this PR fixes it. The probes are the review's evidence and live under `docs/`, outside
    pytest's `testpaths`. They are left as committed. The M-1 probe's slow test, which asserts "no recheck" after the
    advance, would now fail for the same reason.

## 5. No D-4

At the head, compared with `0ea4e489`:

| Identity | Status |
|---|---|
| Runtime-binding census | unchanged: 273 rows, `0cca0414641bf4fbed32b5f42d7c3753a8c47dcdd09d815dcba0658ef8814712` |
| `wp6_1_06h_current_append_manifest.yaml` and `test_wp6_1_06h_append_path_closure.py` | unchanged (blobs `4c895042`, `559d684a`) |
| `test_schema_registry.py` count pin | unchanged: 273 |
| `.research-system/` (schemas, catalogues, configuration) | no file changed |
| `schema_registry.py`, `authority.py` | unchanged |
| `tools/w9_segmentation.py` | unchanged (blob `43e1454d`) |
| Command types | none added |

`git diff --stat 0ea4e489 -- .research-system tools/w9_segmentation.py tests/research_system/smoke
tests/research_system/unit/test_schema_registry.py research_system/schema_registry.py research_system/authority.py`
is empty.

## 6. Tests

| File | What it covers |
|---|---|
| `integration/test_w9_wp9_3_writers.py` | M-1: the skip cases; the absent pointer read without a load; five load failures, each refused with its message (code roots, Git subject, pointer, foundation, schema); `ConflictError`; the ledger and `CommandService` never built on refusal; the M-1 probe as a slow negative control on the v1.2 advance fixture, where after the advance the old checkout's `ars submit` refuses and the control root is byte-identical. m-4: a forged cross-partition ledger refused by `replay`, `rebuild_projection` and `replay_legacy`, and the known-limit boundary with no W9 event |
| `unit/test_w9_inventory_region.py` | M-2: the review's three wrong resolutions refused; the true one admitted; the hash check reached first; no anchor, an out-of-file or non-integer `after_line`, and a selector with a fixed region, each refused; suppression; dated, undated and digit log headings; the property test (seed 20261110, 1,500 inputs, two selectors) |
| `integration/test_w9_wp9_3_inventory_builder.py` | M-3: each region form built and admitted at LR-011 through `submit`; the built fixed-region inventory equal to the hand-built one; a wrong resolution refused through `submit` with nothing appended; the builder's refusals; the frozen-copy rule; reproduction's reports; the CLI round trip writes only its outputs; each forbidden output refused before any input is read; a store marker that is a directory |
| `integration/test_w9_wp9_3_replay.py` | i-2: `observed_at` and three wrong `non_inferences`, each refused. i-1: the instant pinned (docstring) |
| `contracts/test_w9_wp9_3_censuses.py` | i-4: the broad-pattern rule and its fixture. i-5: `binding_check` must be a `.revalidate` attribute (absent, `None`, a name, a lambda and another attribute fail; `b.revalidate` passes) |
| `integration/w9_runtime_harness.py` | The scratch repository gains `sections.md`, a tracked `heading_section` source |

## 7. Verification

Run on the operator machine (Windows, Python 3.13) on 2026-11-10, on the tree of the commit that adds this record. Every
store is a scratch store under `tmp_path`.

- **Regression:** 34 files, one process, 1,464 passed and 1 skipped, in 3,167.6 s (52 min 47 s). The skip is the
  existing `rfc3339-validator absent` skip. The files were:
  - every W9 file;
  - the W11 group the WP9.3-1 review ran: `test_w11_contract_materialization`, `test_w11_expected_catalogue`,
    `test_wp6_6_discovery_{authority,crash_recovery,runtime}`, `test_discovery_dossier` and
    `test_wp6_6_discovery_{activation,architecture,transactions}`;
  - the CLI-submit files: `test_command_cli`, `test_wp64_create_backup` and `test_authority_activate_grant_cli`;
  - the 06h smoke test and `test_schema_registry.py`, both unchanged;
  - `tests/tools/test_research_system_ci_tools.py` and `tests/tools/test_w9_segmentation.py`.
- **Mutation script** (scratch, not committed, as WP9.3-1's was; note §17): **25 of 25** single-guard mutations were
  caught by an executed test failure. The worktree was restored byte for byte after each. The mutations covered:
  - T1: the pointer test, the refusal, and `ConflictError`;
  - T2: the compare, the resolution error, the integer guard, the hash's range, the digit anchor, suppression, and no
    anchor;
  - T3 to T5: the five output guards, the bytes check, both frozen-copy rules, and the `heading_section` region;
  - m-4: the fixed-identity replay check;
  - i-2: both checks;
  - i-4: the broad-pattern rule and one table entry;
  - i-5: the `.revalidate` rule.

  The pass ran before `NON_INFERENCES` moved back to `reader.py`. That move changes the constant's import location
  only, not the guard lines the i-2 mutations weaken.
- **No D-4:** the diff over the protected paths in §5 is empty.
- **Ruff:** check and format are clean on every file this PR changes. Pre-commit ran on every commit.
- **Shard weights:** `tools/research_system_durations.json` gains measured weights for the two new test files, and
  the writers file rises from 20 to 120 s for its new slow control, so `ci-tools`' coverage bar holds.

**Runtime evidence for the open escalation** (WP9.3-1 record §7; not this PR's decision):
- The one new slow test is the M-1 control on the v1.2 advance fixture, at 87.5 s. That matches the review's 85 s for
  the same fixture. The writers file's other new tests take seconds.
- The new unit and builder files take about 2 s and 45 s.
- The slowest tests in the run are the existing W11 replay tests, at 165 s and 163 s, and the binding-head tests, at 81
  to 136 s. Neither file changed in this PR.
- No SPEC suite was run, because no SPEC path changed. The +20% on `test_spec_source.py` is neither re-measured nor
  affected here.

## 8. Obligations and test gaps

- **For WP9.3-1b's independent review** (P-082 item 5): check M-1's control on the real fixture, T2's resolution
  against contract §3 (including §4 item 2's digit-blocker reading), the tools' write-nothing claims, and that no
  protected identity changed (§5).
- **For WP9.3-2:** the builder's batch mode with the ownership list (§4 item 6); it is cut from this PR's merge commit.
- **For Stephen:** whether to drop the later-pin checklist line once this merges (§3); the runtime escalation stays
  open with him (§7).
- **Test gaps, recorded and not closed:**
  - a W11 or generic creation of a reserved `rev_` (§4 item 9);
  - the 69 unpatterned `*_id` fields (§4 item 8);
  - the builder's self-check (`check_resegmentation` on its own output) has no negative control, because the builder
    cannot be given input that makes its own output wrong. It stays as defence in depth.

## 9. Review dispositions

**CodeRabbit's review of `1f6651d1` (5847783527): one inline comment and one nitpick, both checked against the code,
found valid and fixed.** Codex did not review: it hit its usage limit.

| Comment | Finding | Disposition |
|---|---|---|
| 4529307789 | The shared resolver read `after_line: true` as line 1. `reproduce_light_inventory` had no guard of its own, so a record LR-011 refuses could be reported `reproduced: true` | Fixed: `resolve_first_anchor_after` refuses any `after_line` that is not an integer, `bool` included, with "after_line is not a line number". `check_resegmentation`'s own guard is removed, and it now wraps the resolver's refusal with the same message as before. New tests: the resolver refuses `True`, `False`, `"1"`, `1.0` and `None`, and reproduction reports a boolean `after_line` as not reproduced |
| Nitpick (review summary) | The "reordered" `non_inferences` control used a `git_tracked` source, which has one fixed string, so the value was wrong for another reason | Fixed: the reorder control moves to its own test on an `untracked_file` registration and source, whose two fixed strings make the order meaningful. The correct order does not trip the check, and the reversed order is refused |

The `merge-admission` failure on `1f6651d1` was the unresolved inline thread.

**CodeRabbit's review of `73b2e466` (5848603500): four nitpicks, with no inline thread. All four were checked against the
code, found valid and fixed.**

| Finding | Disposition |
|---|---|
| The census compiles each schema `pattern` with Python `re`, which can reject valid ECMA-262 syntax and would raise a bare `re.error` | Fixed, by the stricter of the two suggestions: an uncompilable pattern fails the census with an assertion that names the field (`_admits_w9_id`). Treating it as "no match" would let a field escape a coverage census. New fixture test with `\p{L}` |
| The reorder control's positive half accepted any `IntegrityError` that did not mention `non_inferences` | Fixed: the correct-order `untracked_file` observation was checked to replay clean, so the control now calls `_replay` directly and must succeed |
| `legacy/inventory.py` lacked the research-context header | Fixed: the two header lines precede the docstring |
| `ars legacy inventory reproduce` passed the inventory's `git_blob` to `git cat-file` unchecked, so a value starting with `-` would reach Git as an option | Fixed: the blob must be a 40- or 64-character lowercase hex object ID, or the command refuses before running Git. New test with five bad values, under a `_git` that fails if called |

CodeRabbit's "Docstring Coverage" pre-merge note is answered for the two new private helpers that had no docstring
(`cli._line_pair`, `inventory._level_and_structure`). Test functions follow the repository's existing style.
